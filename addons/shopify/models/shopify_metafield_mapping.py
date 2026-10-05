import hashlib
import logging
import re

from odoo import models, fields, _, api
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import FETCH_METAFIELD_DEFINITIONS
from odoo.addons.shopify.models.misc import extract_numeric_id, exception_message

_logger = logging.getLogger(__name__)

# Task: T9096 - Short owner tokens used in auto-created field names.
OWNER_TYPE_ABBREVIATIONS = {
    'PRODUCT': 'prd',
    'PRODUCTVARIANT': 'var',
    'ORDER': 'ord',
    'CUSTOMER': 'cus',
}

METAFIELD_TYPE = [('single_line_text_field', 'Single Line Text Field'),
                  ('multi_line_text_field', 'Multi Line Text'),
                  ('number_integer', 'Integer'),
                  ('number_decimal', 'Decimal Number'),
                  ('boolean', 'Boolean'),
                  ('date', 'Date'),
                  ('date_time', 'Date and Time'),
                  ('url', 'Url'),
                  ('json', 'JSON'),
                  ('id', 'ID'),
                  ('link', 'Link'),
                  ('weight', 'Weight'),
                  ('volume', 'Volume'),
                  ('color', 'Color'),
                  ('rating', 'Rating'),
                  ('money', 'Money'),
                  ('product_reference', 'Product Reference'),
                  ('list.product_reference', 'Product Reference(list)'),
                  ('variant_reference', 'Variant Reference'),
                  ('list.variant_reference', 'Variant Reference(list)'),
                  ('rich_text_field', 'Rich Text'),
                  ('metaobject_reference', 'Metaobject Reference'),
                  ('list.metaobject_reference', 'Metaobject Reference(list)')]


class ShopifyMetafieldMapping(models.Model):
    _name = 'shopify.metafield.mapping.ts'
    _description = 'Shopify Metafield Mapping'

    resource_id = fields.Many2one('shopify.metafield.resource.ts', string="Resource", required=True, ondelete='cascade',
                                  help="Shopify metafield resource (Product or Variant) to which this metafield belongs.")

    # Related fields for UI
    mk_instance_id = fields.Many2one(related='resource_id.mk_instance_id', store=True, readonly=False, help="Marketplace instance linked to this metafield mapping.")
    odoo_model_id = fields.Many2one(related='resource_id.odoo_model_id', store=True, readonly=False, help="Odoo model where this metafield will be mapped.")

    name = fields.Char(string="Name", help="Name of the Shopify metafield.")
    namespace_and_key = fields.Char(string="Namespace & Key", help="Unique identifier combining namespace and key (e.g., custom.color).")
    namespace = fields.Char(string="Namespace", default="custom", required=True, help="Namespace used to group metafields in Shopify.")
    types = fields.Selection(METAFIELD_TYPE, string='Type', readonly=False, help="Data type of the metafield as defined in Shopify.")

    # Store validation data for minimum_rating/maximum_rating
    scale_min = fields.Float(string="Rating Minimum Scale", help="Minimum value allowed for rating-type metafields.")
    scale_max = fields.Float(string="Rating Maximum Scale", help="Maximum value allowed for rating-type metafields.")

    # --- ODOO MAPPING ---
    odoo_field_id = fields.Many2one(
        'ir.model.fields',
        string="Odoo Field",
        domain="[('id', 'in', compute_odoo_field_ids)]",
        help="Odoo field mapped to this Shopify metafield."
    )
    compute_odoo_field_ids = fields.Many2many('ir.model.fields', string='Compute ID', compute='_compute_odoo_field', compute_sudo=True,
                                              help="Dynamically computed list of Odoo fields that are compatible with the selected Shopify metafield type.")

    odoo_alt_text_field_id = fields.Many2one(
        'ir.model.fields',
        string="Alt Text Field",
        domain="[('model_id', '=', odoo_model_id), ('ttype', 'in', ['char', 'text']), ('store', '=', True), ('name', 'not in', ['id', 'create_uid', 'write_uid', 'create_date', 'write_date'])]",
        help="Optional field used for storing alternative text (used in link-type metafields).",
    )

    odoo_unit_field_id = fields.Many2one('ir.model.fields', string="Odoo Unit Field",
                                         help="Field used to store the unit (e.g., kg, lb, liters) for measurement-type metafields like weight or volume.")
    active_mapping = fields.Boolean(default=True, string="Active", help="Enable this to include the metafield in import and export operations.")

    # Task: T9096 - METAOBJECT REFERENCE
    metaobject_definition_id = fields.Many2one(
        'shopify.metaobject.definition.ts',
        string="Metaobject",
        help="For metaobject_reference metafields: which metaobject definition this metafield points at. "
             "Populated from the 'metaobject_definition_id' validation returned by Shopify."
    )
    metaobject_definition_gid = fields.Char(
        string="Metaobject Definition GID", copy=False,
        help="Raw 'metaobject_definition_id' validation GID from Shopify, kept even when "
             "metaobject_definition_id could not be resolved yet (the definition had not been "
             "imported). Lets _relink_shopify_metaobject_definitions find the right definition "
             "later by a direct id match instead of guessing from the generated field's domain."
    )

    is_found_in_shopify = fields.Boolean(default=True, string="Exists in Shopify", help="Indicates whether this metafield definition currently exists in Shopify or not.")
    mapping_status = fields.Selection([
        ('ready', 'Ready'),
        ('missing', 'Missing Mapping'),
        ('not_found', 'Not Found'),
        ('inactive', 'Inactive')
    ], string="Status", compute='_compute_shopify_metafield_status', store=True, help="Shows mapping status")


    def unlink(self):
        """Task: T9096 - Detach auto-created fields before the mapping disappears."""
        resources = self.mapped('resource_id')
        context_log = self.env.context.get('mk_log_line_dict')
        logs_by_instance = {}

        for mapping in self.filtered(lambda m: m.odoo_field_id and m.odoo_field_id.state == 'manual'):
            field = mapping.odoo_field_id
            field_name, model_name, field_label = field.name, mapping.odoo_model_id.sudo().model, field.field_description
            model = self.env.get(model_name)
            used_count = 0
            if model is not None and field_name in model._fields:
                used_count = model.sudo().search_count([(field_name, '!=', False)])

            mapping.odoo_field_id = False
            bucket = context_log
            if bucket is None:
                bucket = logs_by_instance.setdefault(mapping.mk_instance_id, {'error': [], 'success': []})

            if used_count:
                bucket['error'].append({'log_message': _(
                    "IMPORT METAFIELD DEFINITION: Kept Odoo field %(label)s on %(model)s for metafield %(name)s (%(key)s)\n"
                    "Reason: the metafield no longer exists in Shopify, but %(count)s %(model)s record(s) still hold a value in this field, so Odoo did not delete it.\n"
                    "How to fix:\n"
                    "  • Once you no longer need that data, remove the field %(field)s in Settings > Technical > Fields"
                ) % {'label': field.field_description, 'model': mapping.odoo_model_id.sudo().name, 'name': mapping.name,
                     'key': mapping.namespace_and_key, 'count': used_count, 'field': field_name}})
            else:
                try:
                    # The shared form view still lists this field, and Odoo refuses to delete a field a view uses,
                    # so rebuild the view first (the mapping's field is already cleared, so it is left out).
                    mapping.resource_id._rebuild_shopify_metaobject_view()
                    field.sudo().unlink()
                    bucket['success'].append({'log_message': _(
                        "IMPORT METAFIELD DEFINITION: Removed unused Odoo field %(label)s on %(model)s for metafield %(name)s (%(key)s), because the metafield no longer exists in Shopify"
                    ) % {'label': field_label, 'model': mapping.odoo_model_id.sudo().name, 'name': mapping.name,
                         'key': mapping.namespace_and_key}})
                except Exception as e:
                    bucket['error'].append({'log_message': _(
                        "IMPORT METAFIELD DEFINITION: Could not remove Odoo field %(label)s on %(model)s for metafield %(name)s (%(key)s)\n"
                        "Reason: the metafield no longer exists in Shopify, but the Odoo field is still used on a form view, so Odoo refused to delete it.\n"
                        "How to fix:\n"
                        "  • Remove the field %(field)s in Settings > Technical > Fields"
                    ) % {'label': field_label, 'model': mapping.odoo_model_id.sudo().name, 'name': mapping.name,
                         'key': mapping.namespace_and_key, 'field': field_name}})

        if context_log is None:
            mk_log_obj = self.env['mk.log']
            for instance, mk_log_line_dict in logs_by_instance.items():
                mk_log_id = mk_log_obj.create_update_log(
                    mk_instance_id=instance, operation_type='import', mk_log_line_dict=mk_log_line_dict)
                if not mk_log_id.log_line_ids:
                    mk_log_id.unlink()

        res = super().unlink()
        resources.exists()._rebuild_shopify_metaobject_view()
        return res

    def write(self, vals):
        """
        Task: T9096 - Materialise the backing Odoo field the moment a metaobject mapping is activated.
        """
        res = super().write(vals)
        if vals.get('active_mapping'):
            activated = self.filtered(lambda m: 'metaobject_reference' in (m.types or '') and not m.odoo_field_id)
            if activated:
                activated._sync_shopify_metaobject_odoo_fields()
        return res

    def _sync_shopify_metaobject_odoo_fields(self):
        """Task: T9096 - Create the backing Odoo field for every ACTIVE metaobject-reference mapping.
        Called right after a metafield fetch, and from write() the moment a mapping is
        activated. The field is created once and then kept in step with the mapping: if the
        metaobject definition is imported later, its picker domain is refreshed so the
        merchant only sees entries of the right type. An inactive mapping is left alone -
        that is the whole point of the opt-in.
        """
        metaobject_mappings = self.filtered(lambda m: 'metaobject_reference' in (m.types or '') and m.active_mapping)
        for mapping in metaobject_mappings:
            if not mapping.odoo_field_id:
                mapping.odoo_field_id = mapping._create_shopify_metaobject_odoo_field()
                continue
            expected_domain = mapping._shopify_metaobject_field_domain()
            if mapping.odoo_field_id.state == 'manual' and mapping.odoo_field_id.domain != expected_domain:
                mapping.odoo_field_id.sudo().domain = expected_domain
        if metaobject_mappings:
            metaobject_mappings.mapped('resource_id')._rebuild_shopify_metaobject_view()
        return True

    def _relink_shopify_metaobject_definitions(self):
        """Task: T9096 - Re-resolve metaobject_definition_id for mappings that have none.
        A mapping fetched before its definition existed in Odoo stores
        metaobject_definition_gid (the raw Shopify id) but has no metaobject_definition_id
        yet. This matches that stored id directly against mk_id - a plain lookup, not a
        guess - so it works regardless of which fetch (metafield or metaobject side)
        happens first. Re-run whenever definitions are imported.

        Only the link itself is cosmetic (shown in the UI; import/export resolves a
        metaobject_reference value by GID, never through this field), but the generated
        Odoo field's entry-picker domain is scoped from it (see
        _shopify_metaobject_field_domain), so newly-linked mappings also get their field's
        domain refreshed here instead of waiting for the next metafield fetch.
        """
        definition_obj = self.env['shopify.metaobject.definition.ts']
        relinked = self.browse()
        for mapping in self.filtered('metaobject_definition_gid'):
            definition = definition_obj.search([
                ('mk_id', '=', str(extract_numeric_id(mapping.metaobject_definition_gid))),
                ('mk_instance_id', '=', mapping.mk_instance_id.id),
            ], limit=1)
            if definition:
                mapping.metaobject_definition_id = definition.id
                relinked |= mapping
        if relinked:
            relinked._sync_shopify_metaobject_odoo_fields()
        return True

    def _shopify_metaobject_field_domain(self):
        """Task: T9096 - Restrict the entry picker to the referenced definition, mirroring Shopify.

        Filters on the Shopify type and the instance, never on a definition database id:
        an id baked into a stored domain string goes stale the moment the definition
        record is recreated, and the picker then silently matches nothing.
        Only entries already synced to Shopify (mk_id set) are listed. New can still be used
        from the picker and the new entry is selected, but it only shows in the list once synced.
        """
        self.ensure_one()
        clauses = f"('mk_instance_id', '=', {self.mk_instance_id.id}), ('mk_id', '!=', False)"
        if self.metaobject_definition_id:
            shopify_type = self.metaobject_definition_id.shopify_type
            return f"[('shopify_type', '=', '{shopify_type}'), {clauses}]"
        return f"[{clauses}]"

    def _shopify_metaobject_odoo_field_name(self):
        """Task: T9096 - Build a collision-free technical field name for this mapping.

        The owner-type token keeps PRODUCT and PRODUCTVARIANT apart, which matters
        because product.product _inherits product.template.
        """
        self.ensure_one()

        def _sanitize(value):
            return re.sub(r'\W+', '_', value or '').strip('_').lower()

        mk_instance_id = self.mk_instance_id
        owner_token = OWNER_TYPE_ABBREVIATIONS.get(self.resource_id.shopify_owner_type, 'res')
        prefix = f"x_{mk_instance_id.marketplace}_{mk_instance_id.id}_{owner_token}_"
        base_name = _sanitize(self.namespace_and_key)
        field_name = f"{prefix}{base_name}"

        if len(field_name) > 63:
            hash_suffix = hashlib.md5(base_name.encode()).hexdigest()[:6]
            max_base_len = 63 - len(prefix) - len(hash_suffix) - 1
            field_name = f"{prefix}{base_name[:max_base_len]}_{hash_suffix}"
        return field_name

    def _create_shopify_metaobject_odoo_field(self):
        """Task: T9096 - Create (or reuse) the ir.model.fields storing this metaobject link.

        Returns:
            recordset: Recordset of ir.model.fields.
        """
        self.ensure_one()
        ir_model_fields = self.env['ir.model.fields'].sudo()
        field_name = self._shopify_metaobject_odoo_field_name()
        model_id = self.resource_id.odoo_model_id.sudo()

        existing = ir_model_fields.search([('name', '=', field_name), ('model_id', '=', model_id.id)], limit=1)
        if existing:
            return existing

        is_list = self.types.startswith('list.')
        field_vals = {
            'name': field_name,
            'field_description': f"{self.name or self.namespace_and_key} ({self.mk_instance_id.id})",
            'model_id': model_id.id,
            'ttype': 'many2many' if is_list else 'many2one',
            'relation': 'shopify.metaobject.entry.ts',
            'domain': self._shopify_metaobject_field_domain(),
            'state': 'manual',
        }
        if is_list:
            field_vals.update({
                'relation_table': self._shopify_metaobject_m2m_table_name(field_name),
                'column1': f"{self.env[model_id.model]._table}_id",
                'column2': f"{self.env['shopify.metaobject.entry.ts']._table}_id",
            })
        else:
            field_vals['on_delete'] = 'set null'
        return ir_model_fields.create(field_vals)

    def _shopify_metaobject_m2m_table_name(self, field_name):
        """Task: T9096 - Unique relation table for a list.metaobject_reference field.

        Derived from the field name, which already carries instance + owner type + key,
        so two list metafields can never share a table.
        """
        table_name = f"{field_name}_rel"
        if len(table_name) > 63:
            hash_suffix = hashlib.md5(field_name.encode()).hexdigest()[:6]
            table_name = f"{field_name[:63 - len(hash_suffix) - 5]}_{hash_suffix}_rel"
        return table_name

    @api.constrains('active_mapping', 'odoo_field_id', 'odoo_alt_text_field_id')
    def _check_odoo_field(self):
        """
        T6290 - Ensure no Odoo field is reused across the main (value) slot and
        the alt-text slot, on the same mapping or across active mappings.
        """
        for record in self:
            if not record.active_mapping:
                continue

            main = record.odoo_field_id
            alt = record.odoo_alt_text_field_id

            if not main and not alt:
                continue

            instance_name = record.mk_instance_id.name or '(no instance)'

            if main and alt and main.id == alt.id:
                raise MarketplaceException(_(
                    "SHOPIFY METAFIELD CONFIGURATION: Cannot save metafield '%(record_name)s' "
                    "on instance '%(instance_name)s'\n"
                    "\n"
                    "Issue: '%(field_description)s' is selected as both 'Odoo Field' "
                    "and 'Alt Text Field'\n"
                    "\n"
                    "How to fix: Pick a different Odoo field for one of the two slots, "
                    "or leave 'Alt Text Field' empty if not needed."
                ) % {
                    'record_name': record.name,
                    'instance_name': instance_name,
                    'field_description': main.field_description,
                })

            others = self.search([
                ('id', '!=', record.id),
                ('active_mapping', '=', True),
            ])

            def _raise_if_field_in_use(used_field, current_slot_label):
                conflict = others.filtered(
                    lambda m: (m.odoo_field_id and m.odoo_field_id.id == used_field.id)
                              or (m.odoo_alt_text_field_id and m.odoo_alt_text_field_id.id == used_field.id)
                )
                if not conflict:
                    return
                other = conflict[0]
                other_slot = (
                    'Odoo Field'
                    if (other.odoo_field_id and other.odoo_field_id.id == used_field.id)
                    else 'Alt Text Field'
                )
                other_instance_name = other.mk_instance_id.name or ''
                raise MarketplaceException(_(
                    "SHOPIFY METAFIELD CONFIGURATION: Cannot save metafield '%(record_name)s' "
                    "on instance '%(instance_name)s'\n"
                    "\n"
                    "Issue: '%(field_description)s' (selected as '%(current_slot_label)s') "
                    "is already used as '%(other_slot)s' by metafield '%(other_name)s' "
                    "on instance '%(other_instance_name)s'\n"
                    "\n"
                    "How to fix: Pick a different Odoo field, or remove it from "
                    "metafield '%(other_name)s' first."
                ) % {
                    'record_name': record.name,
                    'instance_name': instance_name,
                    'field_description': used_field.field_description,
                    'current_slot_label': current_slot_label,
                    'other_slot': other_slot,
                    'other_name': other.name,
                    'other_instance_name': other_instance_name,
                })

            if main:
                _raise_if_field_in_use(main, 'Odoo Field')
            if alt:
                _raise_if_field_in_use(alt, 'Alt Text Field')

    @api.depends('types')
    def _compute_odoo_field(self):
        """
        T6290 - Compute compatible Odoo fields based on selected Shopify metafield type.
        """
        for record in self:
            if not record.types or not record.odoo_model_id:
                record.compute_odoo_field_ids = []
                continue

            allowed_odoo_types = []
            domain = []

            if record.types in ['single_line_text_field', 'url', 'id', 'link', 'color']:
                allowed_odoo_types = ['char']

            elif record.types == 'multi_line_text_field':
                allowed_odoo_types = ['text']

            elif record.types == 'json':
                allowed_odoo_types = ['text']

            elif record.types == 'number_integer':
                allowed_odoo_types = ['integer']

            elif record.types in ['number_decimal', 'rating', 'weight', 'volume']:
                allowed_odoo_types = ['float']

            elif record.types == 'boolean':
                allowed_odoo_types = ['boolean']

            elif record.types == 'date':
                allowed_odoo_types = ['date']

            elif record.types == 'date_time':
                allowed_odoo_types = ['datetime']

            elif record.types == 'money':
                allowed_odoo_types = ['float', 'monetary']

            elif record.types == 'rich_text_field':
                allowed_odoo_types = ['html']

            elif record.types in ['product_reference', 'variant_reference']:
                allowed_odoo_types = ['many2one']
                if record.types == 'product_reference':
                    model_name = 'product.template'
                else:
                    model_name = 'product.product'
                domain.append(('relation', '=', model_name))

            elif record.types in ['list.product_reference', 'list.variant_reference']:
                allowed_odoo_types = ['many2many']
                if record.types == 'list.product_reference':
                    model_name = 'product.template'
                else:
                    model_name = 'product.product'
                domain.append(('relation', '=', model_name))

            elif 'metaobject_reference' in record.types:
                allowed_odoo_types = ['many2many'] if record.types.startswith('list.') else ['many2one']
                domain.append(('relation', '=', 'shopify.metaobject.entry.ts'))

            # Search ir.model.fields for the specific model and allowed types
            # We also filter out System fields (create_uid, etc.) and non-stored fields if necessary
            domain.extend([
                ('model_id', '=', record.odoo_model_id.id),
                ('ttype', 'in', allowed_odoo_types),
                ('store', '=', True),
                ('name', 'not in', ['id', 'create_uid', 'write_uid', 'create_date', 'write_date'])
            ])
            record.compute_odoo_field_ids = self.env['ir.model.fields'].sudo().search(domain)

    @api.depends('active_mapping', 'odoo_field_id', 'is_found_in_shopify')
    def _compute_shopify_metafield_status(self):
        """
        T6290 - Compute the mapping status of Shopify metafields.
        """
        for record in self:
            if not record.is_found_in_shopify:
                record.mapping_status = 'not_found'
            elif not record.active_mapping:
                record.mapping_status = 'inactive'
            elif not record.odoo_field_id and record.active_mapping:
                record.mapping_status = 'missing'
            elif record.odoo_field_id and record.active_mapping:
                record.mapping_status = 'ready'

    def action_fetch_shopify_metafields(self):
        """
        T6290 - Fetch metafield definitions from Shopify and sync them into Odoo.
        Raises:
            MarketplaceException: If resource is not found or metafield sync is not active.
        """
        resource_id = self.env.context.get('default_resource_id')
        if not resource_id:
            raise MarketplaceException(_("Resource Not Found!"))
        resource = self.env['shopify.metafield.resource.ts'].browse(resource_id)
        mk_instance_id = resource.mk_instance_id

        if mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("Please confirm the instance before fetching metafields."))
        if not mk_instance_id.enable_metafield:
            raise MarketplaceException(_("Metafield functionality is disabled for this instance."))

        mk_log_id = self.env['mk.log'].create_update_log(
            mk_instance_id=mk_instance_id,
            operation_type='import'
        )
        mk_log_line_dict = {'error': [], 'success': []}

        try:
            if not resource.active_sync:
                raise MarketplaceException(_("Please Active metafield configuration!!!"))
            resource_metafield_definitions_list = self.with_context(mk_log_line_dict=mk_log_line_dict)._fetch_shopify_metafield_definitions(resource, mk_instance_id)
            if resource_metafield_definitions_list:
                self.create_or_update_shopify_resource_metafield_definitions(resource_metafield_definitions_list, mk_instance_id, resource)
        except Exception as e:
            if resource.active_sync:
                reason = exception_message(e)
                fix = _("Check that the instance is connected, then click Fetch Latest again")
            else:
                reason = _("Metafield Configuration is not active.")
                fix = _("Open the instance, go to the Metafields tab, turn on the switch on the %s card, then click Fetch Latest again") % resource.name
            log_message = _(
                "IMPORT METAFIELD DEFINITION: Failed to fetch %(resource)s for instance (%(instance)s)\n"
                "Reason: %(reason)s\n"
                "How to fix:\n"
                "  • %(fix)s"
            ) % {'resource': resource.name, 'instance': mk_instance_id.name, 'reason': reason, 'fix': fix}
            mk_log_line_dict['error'].append({'log_message': log_message})

        self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_instance_id=mk_instance_id, operation_type='import', mk_log_line_dict=mk_log_line_dict)
        if not mk_log_id.log_line_ids:
            mk_log_id.unlink()
        return True

    def _fetch_shopify_metafield_definitions(self, resource, mk_instance_id):
        """
        T6290 - Fetch all metafield definitions from Shopify using pagination.
        Args:
            resource (recordset): Recordset of shopify.metafield.resource.ts.
            mk_instance_id (recordset): Recordset of mk.instance.
        Returns:
            list: List of metafield definition dictionaries fetched from Shopify
        Raises:
            None: Errors are handled internally and logged in the system.
        """
        try:
            mk_instance_id.connection_to_shopify()
            mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
            shopify_resource_metafield_list = []
            cursor = None

            while True:
                variables = {"ownerType": resource.shopify_owner_type, "first": 250, "metafieldResourceCursor": cursor}
                res = mk_instance_id.execute_graphql_query(FETCH_METAFIELD_DEFINITIONS, variables=variables)
                if res and res.get('errors'):
                    log_message = _("IMPORT METAFIELD DEFINITION: Shopify error while fetching metafields for %s - %s") % (resource.resource_name, res.get('errors'))
                    mk_log_line_dict['error'].append({'log_message': log_message})
                    break

                shopify_product_metafield_res = res and res.get('data', {}) and res.get('data', {}).get('metafieldDefinitions', {}) and res.get('data', {}).get('metafieldDefinitions',
                                                                                                                                                                {}).get('nodes', [])
                if shopify_product_metafield_res:
                    shopify_resource_metafield_list.extend(shopify_product_metafield_res)
                    page_info = res.get('data', {}).get('metafieldDefinitions', {}).get('pageInfo', {})
                    if not page_info.get('hasNextPage', False):
                        break
                    cursor = page_info.get('endCursor', None)
                else:
                    break
            return shopify_resource_metafield_list
        except Exception as e:
            log_message = f"IMPORT METAFIELD DEFINITION: Error while fetching metafields for {resource.resource_name}: {str(e)}"
            mk_log_line_dict and mk_log_line_dict['error'].append({'log_message': log_message})
            return False

    def create_or_update_shopify_resource_metafield_definitions(self, shopify_product_metafield_list, mk_instance_id, resource_rec):
        """
        T6290 - Create or update Shopify metafield definitions in Odoo.
        Args:
            shopify_product_metafield_list (list): List of metafield definition dictionaries from Shopify.
            mk_instance_id (recordset): Recordset of mk.instance.
            resource_rec (recordset): Recordset of shopify.metafield.resource.ts.
        """
        existing_metafield_mapping_ids = self.search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('resource_id', '=', resource_rec.id),
        ])
        existing_metafield_mapping_ids.write({'is_found_in_shopify': False})

        vals_list = []
        for metafield in shopify_product_metafield_list:
            namespace_and_key = f"{metafield.get('namespace')}.{metafield.get('key')}"
            metafield_type = metafield.get('type', {}).get('name')

            existing_mapping = existing_metafield_mapping_ids.filtered(lambda x: x.namespace_and_key == namespace_and_key)
            # Mark as found if it exists in Shopify
            if existing_mapping:
                update_vals = {'is_found_in_shopify': True, 'name': metafield.get('name')}
                validations = {v.get('name'): v.get('value') for v in metafield.get('validations') or []}

                if any(t[0] == metafield_type for t in METAFIELD_TYPE):
                    update_vals['types'] = metafield_type
                elif existing_mapping.types != metafield_type:
                    update_vals['active_mapping'] = False
                    mk_log_line_dict = self.env.context.get('mk_log_line_dict')
                    if mk_log_line_dict is not None:
                        mk_log_line_dict['error'].append({'log_message': _(
                            "IMPORT METAFIELD DEFINITION: Metafield '%(name)s' (%(key)s) changed type in Shopify to "
                            "'%(new_type)s', which this connector does not support. The mapping was deactivated to "
                            "avoid writing wrong values. Remove the mapping or change the type back in Shopify."
                        ) % {'name': metafield.get('name'), 'key': namespace_and_key, 'new_type': metafield_type}})

                if metafield_type == 'rating':
                    update_vals.update({
                        'scale_min': float(validations.get('scale_min') or 0.0),
                        'scale_max': float(validations.get('scale_max') or 0.0),
                    })
                if 'metaobject_reference' in (metafield_type or ''):
                    referenced_gid = validations.get('metaobject_definition_id')
                    update_vals['metaobject_definition_gid'] = referenced_gid
                    update_vals['metaobject_definition_id'] = self._resolve_metaobject_definition(
                        referenced_gid, mk_instance_id)
                existing_mapping.write(update_vals)

            if not existing_mapping:
                if not any(t[0] == metafield_type for t in METAFIELD_TYPE):
                    continue
                vals_list.append(self.prepare_shopify_resource_metafield_defination_vals(metafield, resource_rec, mk_instance_id))

        if vals_list:
            self.create(vals_list)

        # Delete definitions that no longer exist in Shopify
        deleted_mappings = existing_metafield_mapping_ids.filtered(lambda x: not x.is_found_in_shopify)
        if deleted_mappings:
            deleted_mappings.write({'active_mapping': False})
            deleted_mappings.unlink()

        # Materialise the backing Odoo field for metaobject references.
        self.search([('mk_instance_id', '=', mk_instance_id.id),
                     ('resource_id', '=', resource_rec.id)])._sync_shopify_metaobject_odoo_fields()

    def auto_create_unit_field_for_shopify_metafield(self, namespace_and_key, name, metafield_type, resource_id, mk_instance_id):
        """
        T6290 - Create or retrieve a unit selection field for Shopify measurement metafields.
        Args:
            namespace_and_key (str): Unique identifier of the metafield (namespace.key).
            name (str): Display name of the metafield.
            metafield_type (str): Type of metafield (e.g., weight, volume).
            resource_id (recordset): Recordset of shopify.metafield.resource.ts.
            mk_instance_id (recordset): Recordset of mk.instance.
        Returns:
            int: ID of the created or existing ir.model.fields record.
        """

        def _sanitize(value):
            """Convert any string into a valid SQL/Python identifier fragment."""
            return re.sub(r'\W+', '_', value or '').strip('_').lower()

        ir_model_fields = self.env['ir.model.fields'].sudo()
        prefix = f"x_{mk_instance_id.marketplace}_{mk_instance_id.id}_"
        suffix = "_unit"
        unit_field_name = _sanitize(namespace_and_key)
        origin_field_name = f"{prefix}{unit_field_name}{suffix}"

        if len(origin_field_name) > 63:
            # Too long → truncate + hash
            hash_suffix = hashlib.md5(unit_field_name.encode()).hexdigest()[:6]
            max_base_len = 63 - len(prefix) - len(suffix) - len(hash_suffix) - 1
            short_base = unit_field_name[:max_base_len]
            origin_field_name = f"{prefix}{short_base}_{hash_suffix}{suffix}"

        # Check if we already created it
        unit_field = ir_model_fields.search([('name', '=', origin_field_name), ('model_id', '=', resource_id.odoo_model_id.id)], limit=1)

        if not unit_field:
            selection_options = "[]"
            if metafield_type == 'weight':
                selection_options = [('GRAMS', 'Grams'), ('KILOGRAMS', 'KG'), ('POUNDS', 'LB'), ('OUNCES', 'Oz')]
            elif metafield_type == 'volume':
                selection_options = [('MILLILITERS', 'Milliliters(ML)'), ('CENTILITERS', 'Centiliters(CL)'), ('LITERS', 'Liters(L)'), ('CUBIC_METERS', 'Cubic meters(M3)'),
                                     ('FLUID_OUNCES', 'Fluid ounces(Fl Oz)'), ('PINTS', 'Pints(PT)'), ('QUARTS', 'Quarts(QT)'), ('GALLONS', 'Gallons(GAL)'),
                                     ('IMPERIAL_FLUID_OUNCES', 'Imperial Fluid Ounces(Imp Fl Oz)'), ('IMPERIAL_PINTS', 'Imperial Pints(Imp Pt)'),
                                     ('IMPERIAL_QUARTS', 'Imperial Quarts(Imp Qt)'), ('IMPERIAL_GALLONS', 'Imperial Gallons(Imp Gal)')]

            unit_field = ir_model_fields.sudo().create({
                'name': origin_field_name,
                'field_description': f"{name} Unit ({mk_instance_id.id})",
                'model_id': resource_id.odoo_model_id.id,
                'ttype': 'selection',
                'selection': str(selection_options),
                'state': 'manual',  # Marks it as a custom field
            })

        return unit_field.id

    def prepare_shopify_resource_metafield_defination_vals(self, metafield_dict, resource_rec, mk_instance_id):
        """
        T6290 - Prepare values for creating or updating Shopify metafield mapping records.
        Args:
            metafield_dict (dict): Shopify metafield definition data.
            resource_rec (recordset): Recordset of shopify.metafield.resource.ts.
            mk_instance_id (recordset): Recordset of mk.instance.
        Returns:
            dict: Values dictionary for shopify.metafield.mapping.ts record creation.
        """
        namespace_and_key = f"{metafield_dict.get('namespace')}.{(metafield_dict.get('key'))}"
        metafield_type = metafield_dict.get('type', {}).get('name')
        metafield_vals = {}

        if metafield_type in ('weight', 'volume'):
            # Auto-create the unit field on the product
            unit_field_id = self.auto_create_unit_field_for_shopify_metafield(
                namespace_and_key=namespace_and_key,
                name=metafield_dict.get('name', ''),
                metafield_type=metafield_type,
                resource_id=resource_rec,
                mk_instance_id=mk_instance_id,
            )
            metafield_vals.update({
                'odoo_unit_field_id': unit_field_id,
            })

        metafield_vals.update({
            'name': metafield_dict.get('name'),
            'namespace': metafield_dict.get('namespace'),
            'namespace_and_key': namespace_and_key,
            'types': metafield_type,
            'is_found_in_shopify': True,
            'resource_id': resource_rec.id,
        })

        if 'metaobject_reference' in (metafield_type or ''):
            metafield_vals['active_mapping'] = False

        validations = {v.get('name'): v.get('value') for v in metafield_dict.get('validations') or []}
        if metafield_type == 'rating':
            metafield_vals.update({
                'scale_min': float(validations.get('scale_min') or 0.0),
                'scale_max': float(validations.get('scale_max') or 0.0),
            })
        if 'metaobject_reference' in (metafield_type or ''):
            referenced_gid = validations.get('metaobject_definition_id')
            metafield_vals['metaobject_definition_gid'] = referenced_gid
            metafield_vals['metaobject_definition_id'] = self._resolve_metaobject_definition(
                referenced_gid, mk_instance_id)
        return metafield_vals

    def _resolve_metaobject_definition(self, referenced_gid, mk_instance_id):
        """Resolve a Shopify MetaobjectDefinition GID to a local definition record.

        Args:
            referenced_gid (str): Value of the 'metaobject_definition_id' validation.
            mk_instance_id (recordset): Recordset of mk.instance.
        Returns:
            int | bool: Id of shopify.metaobject.definition.ts, or False when not imported yet.
        """
        if not referenced_gid:
            return False
        definition = self.env['shopify.metaobject.definition.ts'].search([
            ('mk_id', '=', str(extract_numeric_id(referenced_gid))),
            ('mk_instance_id', '=', mk_instance_id.id),
        ], limit=1)
        return definition.id or False