import logging

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import FETCH_METAOBJECT_DEFINITIONS, DELETE_DEF_MUTATION
from odoo.addons.shopify.models.misc import extract_numeric_id, exception_message

_logger = logging.getLogger(__name__)


class ShopifyMetaobjectDefinition(models.Model):
    _name = 'shopify.metaobject.definition.ts'
    _description = 'Shopify Metaobject Definition'
    _order = 'name'
    _rec_name = 'name'

    mk_instance_id = fields.Many2one('mk.instance', string="Instance", required=True, ondelete='cascade',
                                     help="Marketplace instance this metaobject definition belongs to.")
    mk_id = fields.Char(string="Shopify ID", index=True,
                        help="Numeric part of the Shopify MetaobjectDefinition GID.")
    shopify_type = fields.Char(string="Type", required=True,
                               help="Shopify metaobject type handle, e.g. 'product_highlight'.")
    name = fields.Char(string="Name", help="Display name of the definition as shown in Shopify.")

    admin_access = fields.Selection([
        ('MERCHANT_READ', 'Read Only'),
        ('MERCHANT_READ_WRITE', 'Merchant Only'),
        ('PUBLIC_READ_WRITE', 'Merchant and Apps'),
    ], string="Admin API Access", help="Shopify's own access.admin value for this definition. This is the real, "
        "documented signal for whether an app may write entries - NOT the type name: a 'shopify--' prefixed "
        "definition can be PUBLIC_READ_WRITE, and a merchant-created one can be MERCHANT_READ_WRITE. Only "
        "PUBLIC_READ_WRITE lets this connector create or update entries; the other values mean Shopify itself "
        "restricts writes to the Shopify admin UI, regardless of what the type is named.")
    is_app_writable = fields.Boolean(string="Writable by Apps", compute='_compute_is_shopify_app_writable', store=True,
                                     help="True only when admin_access is PUBLIC_READ_WRITE. Used by the "
                                          "push/delete guard on entries.")

    field_ids = fields.One2many('shopify.metaobject.field.ts', 'definition_id', string="Fields",
                                help="Schema of this metaobject, imported from Shopify.")
    entry_ids = fields.One2many('shopify.metaobject.entry.ts', 'definition_id', string="Entries",
                                help="Entries (records) of this metaobject definition.")

    entry_count = fields.Integer(string="Entry Count", compute='_compute_shopify_entry_count')

    _uniq_type_per_instance = models.Constraint(
        "UNIQUE(mk_instance_id, shopify_type)",
        "This metaobject type already exists for this instance.")

    def _normalize_shopify_admin_access(self, value):
        """Task: T9096 - Guard against a deprecated enum value (PRIVATE, PUBLIC_READ) Shopify might still
        return on an older API version: store it as unknown rather than let a value outside
        our Selection's 3 options fail the write.
        """
        return value if value in ('MERCHANT_READ', 'MERCHANT_READ_WRITE', 'PUBLIC_READ_WRITE') else False

    @api.depends('admin_access')
    def _compute_is_shopify_app_writable(self):
        for record in self:
            record.is_app_writable = record.admin_access == 'PUBLIC_READ_WRITE'

    @api.depends('entry_ids')
    def _compute_shopify_entry_count(self):
        for record in self:
            record.entry_count = len(record.entry_ids)

    def unlink(self):
        """Task: T9096 - Block removing a definition while any of its entries is still referenced.

        entry_ids/field_ids cascade at the database level, which bypasses
        shopify.metaobject.entry.ts's own unlink() guard entirely - this check is what
        actually protects a definition's data, both for the standard list/form delete and
        for the auto-cleanup below.
        """
        for definition in self:
            referenced = definition.entry_ids.filtered(lambda e: e._is_shopify_entry_referenced())
            if referenced:
                raise MarketplaceException(_(
                    "SHOPIFY METAOBJECT: Cannot remove metaobject %(definition)s\n"
                    "Reason: %(count)s of its entries are still in use by other records: %(names)s\n"
                    "How to fix:\n"
                    "  • Remove those entries from where they are used, then remove this metaobject again"
                ) % {'definition': definition.name or definition.shopify_type, 'count': len(referenced),
                     'names': ', '.join(referenced.mapped(lambda e: e._shopify_entry_label()))})
        return super().unlink()

    def action_delete_shopify_definition(self):
        """Task: T9096 - Delete this metaobject definition in Shopify (if pushed), then remove it from Odoo.

        Deletes the definition itself, not just an entry - Shopify cascades this to every
        entry of the type. Only offered when is_app_writable (see push/delete guard on
        shopify.metaobject.entry.ts for the same access.admin check).
        """
        if not self.mk_instance_id.enable_metaobject:
            raise MarketplaceException(_(
                "SHOPIFY METAOBJECT: Cannot delete metaobject %(definition)s\n"
                "Reason: Metaobject Functionality is turned off for instance (%(instance)s)\n"
                "How to fix:\n"
                "  • Open the instance, go to the Metafields tab and turn on Metaobjects"
            ) % {'definition': self.display_name, 'instance': self.mk_instance_id.name})
        if self.mk_id:
            self.mk_instance_id.connection_to_shopify()
            variables = {"id": f"gid://shopify/MetaobjectDefinition/{self.mk_id}"}
            response = self.mk_instance_id.execute_graphql_query(DELETE_DEF_MUTATION, variables=variables)

            # Check for Shopify API errors (e.g., Shopify blocking deletion because it's in use)
            user_errors = response.get('data', {}).get('metaobjectDefinitionDelete', {}).get('userErrors', [])
            if user_errors:
                error_msg = ", ".join([err.get('message', 'Unknown error') for err in user_errors])
                raise MarketplaceException(_(
                    "SHOPIFY METAOBJECT: Failed to delete metaobject %(def_name)s from Shopify\n"
                    "Reason: Shopify said: %(error)s\n"
                    "How to fix:\n"
                    "  • Resolve it in Shopify admin (Content > Metaobjects), then click Delete Metaobject again"
                ) % {'def_name': self.display_name, 'error': error_msg})

        self.unlink()
        return {
            'name': _('Metaobject Definitions'),
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.metaobject.definition.ts',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def _cleanup_stale_shopify_definitions(self, mk_instance_id, received_types, mk_log_line_dict):
        """Task: T9096 - Remove definitions that no longer exist in Shopify, after a complete fetch.

        A definition still holding a referenced entry is kept and reported instead of
        being removed, per the guard in unlink().

        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            received_types (set): Shopify metaobject types seen in this fetch.
            mk_log_line_dict (dict): Dictionary to collect log messages.
        """
        stale = self.search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('shopify_type', 'not in', list(received_types)),
        ])
        if not stale:
            return

        removed, kept = [], []
        for definition in stale:
            label = definition.name or definition.shopify_type
            try:
                definition.unlink()
                removed.append(label)
            except MarketplaceException:
                kept.append(label)

        if removed:
            mk_log_line_dict['success'].append({'log_message': _(
                "IMPORT METAOBJECT DEFINITION: Removed metaobject(s) %(names)s from Odoo because they no longer exist in Shopify"
            ) % {'names': ', '.join(removed)}})
        if kept:
            mk_log_line_dict['error'].append({'log_message': _(
                "IMPORT METAOBJECT DEFINITION: Kept metaobject(s) %(names)s that no longer exist in Shopify\n"
                "Reason: some of their entries are still in use by other records in Odoo\n"
                "How to fix:\n"
                "  • Remove those entries from where they are used, then delete the metaobject(s) in Marketplaces > Shopify > Catalogs > Metaobjects"
            ) % {'names': ', '.join(kept)}})

    def action_open_shopify_entries(self):
        """Task: T9096 - Open the entries of this definition."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Entries',
            'res_model': 'shopify.metaobject.entry.ts',
            'view_mode': 'list,form',
            'domain': [('definition_id', '=', self.id)],
            'context': {
                'default_definition_id': self.id,
                'default_mk_instance_id': self.mk_instance_id.id,
            },
        }

    def action_add_shopify_entry(self):
        """Task: T9096 - Open a blank entry form pre-filled with this definition."""
        self.ensure_one()
        if not self.mk_instance_id.enable_metaobject:
            raise MarketplaceException(_(
                "UPDATE METAOBJECT ENTRY: Cannot add an entry to metaobject %(definition)s for instance (%(instance)s)\n"
                "Reason: Metaobject Functionality is turned off for this instance\n"
                "How to fix:\n"
                "  • Go to Marketplaces > Configuration > Instance, open the instance, go to the Metafields tab, and turn on Metaobject Functionality."
            ) % {'definition': self.display_name, 'instance': self.mk_instance_id.name})
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Entry',
            'res_model': 'shopify.metaobject.entry.ts',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_definition_id': self.id,
                'default_mk_instance_id': self.mk_instance_id.id,
            },
        }

    def _shopify_instance_ids_from_active_domain(self):
        """Task: T9096 - Instance ids the list's current search is narrowed to, if any.

        A list header button gets the list's active domain in its context (`active_domain`),
        and that domain includes the left Instance panel's selection as an
        ('mk_instance_id', '=', id) leaf. Choosing "All" leaves no such leaf.
        """
        instance_ids = set()
        for leaf in self.env.context.get('active_domain') or []:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == 'mk_instance_id' \
                    and leaf[1] in ('=', 'in'):
                value = leaf[2]
                instance_ids.update(value if isinstance(value, (list, tuple)) else [value])
        return [instance_id for instance_id in instance_ids if instance_id and isinstance(instance_id, int)]

    def action_fetch_shopify_metaobject_definitions(self):
        """Task: T9096 - Fetch all metaobject definitions (and their fields) from Shopify for an instance.

        The instance is taken from the context when the list is opened from an instance, else
        from the Instance selected in the list's left panel; with neither (the panel on
        "All"), every confirmed Shopify instance is refreshed.
        """
        instance_obj = self.env['mk.instance']
        instance_id = self.env.context.get('default_mk_instance_id') or self.env.context.get('mk_instance_id')
        instance_ids = [instance_id] if instance_id else self._shopify_instance_ids_from_active_domain()
        instances = instance_obj.browse(instance_ids) if instance_ids else instance_obj.search(
            [('marketplace', '=', 'shopify'), ('state', '=', 'confirmed')])
        if not instances:
            raise MarketplaceException(_(
                "IMPORT METAOBJECT DEFINITION: Cannot fetch metaobject definitions\n"
                "Reason: no confirmed Shopify instance was found\n"
                "How to fix:\n"
                "  • Confirm the Shopify instance, then click Fetch Definitions again"
            ))
        if not instances.filtered('enable_metaobject'):
            raise MarketplaceException(_(
                "IMPORT METAOBJECT DEFINITION: Cannot fetch metaobject definitions for instance (%(instances)s)\n"
                "Reason: Metaobject Functionality is turned off\n"
                "How to fix:\n"
                "  • Go to Marketplaces > Configuration > Instance, open the instance, go to the Metafields tab, and turn on Metaobject Functionality."
            ) % {'instances': ', '.join(instances.mapped('name'))})

        for instance in instances:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=instance, operation_type='import')
            mk_log_line_dict = {'error': [], 'success': []}
            if not instance.enable_metaobject:
                mk_log_line_dict['error'].append({'log_message': _(
                    "IMPORT METAOBJECT DEFINITION: Skipped fetching metaobjects for instance (%(instance)s)\n"
                    "Reason: Metaobject Functionality is turned off for this instance\n"
                    "How to fix:\n"
                    "  • Open the instance, go to the Metafields tab and turn on Metaobjects, then click Fetch Definitions again"
                ) % {'instance': instance.name}})
            else:
                try:
                    definitions, is_complete = self._fetch_shopify_metaobject_definitions(instance, mk_log_line_dict)
                    if definitions:
                        self._create_or_update_shopify_metaobject_definitions(definitions, instance)
                    if is_complete:
                        received_types = {d.get('type') for d in definitions if d.get('type')}
                        self._cleanup_stale_shopify_definitions(instance, received_types, mk_log_line_dict)

                    if is_complete:
                        current_definitions = self.search([
                            ('mk_instance_id', '=', instance.id),
                            ('shopify_type', 'in', list(received_types)),
                        ])
                        if current_definitions:
                            # Entries fetched as part of this click write into this click's log.
                            self.env['shopify.metaobject.entry.ts'].with_context(
                                mk_log_id=mk_log_id).import_shopify_entries_for_definitions(
                                current_definitions, instance, mk_log_line_dict)
                except Exception as e:
                    mk_log_line_dict['error'].append({'log_message': _(
                        "IMPORT METAOBJECT DEFINITION: Failed to fetch metaobjects for instance (%(instance)s)\n"
                        "Reason: %(error)s"
                    ) % {'instance': instance.name, 'error': exception_message(e)}})
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_instance_id=instance,
                                                 operation_type='import', mk_log_line_dict=mk_log_line_dict)
            if not mk_log_id.log_line_ids:
                mk_log_id.unlink()
        return True

    def _fetch_shopify_metaobject_definitions(self, mk_instance_id, mk_log_line_dict):
        """Page through metaobjectDefinitions and return the raw nodes.

        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            mk_log_line_dict (dict): Dictionary used to collect error and success log messages.
        Returns:
            tuple: (list of metaobject definition dicts, bool - True when every page was read
                without error, i.e. the list can be trusted as complete).
        """
        mk_instance_id.connection_to_shopify()
        definitions, cursor, is_complete = [], None, True
        while True:
            variables = {"first": 250, "metaobjectDefinitionCursor": cursor}
            res = mk_instance_id.execute_graphql_query(FETCH_METAOBJECT_DEFINITIONS, variables=variables)
            if res and res.get('errors'):
                mk_log_line_dict['error'].append({'log_message': _(
                    "IMPORT METAOBJECT DEFINITION: Could not fetch metaobjects from Shopify for instance (%(instance)s)\n"
                    "Reason: Shopify returned an error: %(error)s"
                ) % {'instance': mk_instance_id.name, 'error': res.get('errors')}})
                is_complete = False
                break
            data = ((res or {}).get('data') or {}).get('metaobjectDefinitions') or {}
            nodes = data.get('nodes') or []
            if not nodes:
                break
            definitions.extend(nodes)
            page_info = data.get('pageInfo') or {}
            if not page_info.get('hasNextPage'):
                break
            cursor = page_info.get('endCursor')
        return definitions, is_complete

    def _create_or_update_shopify_metaobject_definitions(self, definitions, mk_instance_id):
        """Task: T9096 - Create or update definitions and their field schema.

        Every field is imported, including Shopify types the connector cannot convert;
        those are flagged is_supported=False, shown read-only and never pushed back.

        Backstop, not the primary UX: this is the one place every metaobject-definition
        write actually happens, reached both from the explicit Fetch actions (already
        gated, with a clear per-instance log) and from auto-import triggered deep inside an
        ordinary product/order/customer sync (_resolve_shopify_definitions_for_nodes). Raising here
        guarantees no definition is ever written while the instance has metaobjects
        disabled, regardless of which path got here; the caller's own try/except logs it.
        """
        if not mk_instance_id.enable_metaobject:
            raise MarketplaceException(_(
                "Metaobject Functionality is turned off for instance (%(instance)s)"
            ) % {'instance': mk_instance_id.name})
        field_obj = self.env['shopify.metaobject.field.ts']
        existing = self.search([('mk_instance_id', '=', mk_instance_id.id)])
        by_type = {d.shopify_type: d for d in existing}

        for definition_dict in definitions:
            shopify_type = definition_dict.get('type')
            if not shopify_type:
                continue
            vals = {
                'mk_instance_id': mk_instance_id.id,
                'mk_id': str(extract_numeric_id(definition_dict.get('id'))),
                'shopify_type': shopify_type,
                'name': definition_dict.get('name'),
                'admin_access': self._normalize_shopify_admin_access((definition_dict.get('access') or {}).get('admin')),
            }
            definition = by_type.get(shopify_type)
            if definition:
                definition.write(vals)
            else:
                definition = self.create(vals)
                by_type[shopify_type] = definition

            existing_fields = {f.key: f for f in definition.field_ids}
            received_keys = set()
            for field_dict in definition_dict.get('fieldDefinitions') or []:
                # Import every field, including types the connector cannot convert: they are
                # shown read-only and never pushed, so Shopify keeps its own value.
                field_type = (field_dict.get('type') or {}).get('name')
                key = field_dict.get('key')
                received_keys.add(key)
                field_vals = self._prepare_shopify_metaobject_field_vals(field_dict, field_type, definition)
                if key in existing_fields:
                    existing_fields[key].write(field_vals)
                else:
                    field_obj.create(dict(field_vals, definition_id=definition.id, key=key))

            self.env['shopify.metafield.mapping.ts'].search([
                ('mk_instance_id', '=', mk_instance_id.id),
                ('metaobject_definition_id', '=', False),
                ('types', 'in', ['metaobject_reference', 'list.metaobject_reference']),
            ])._relink_shopify_metaobject_definitions()

            stale = definition.field_ids.filtered(lambda f: f.key not in received_keys)
            if stale:
                value_count = self.env['shopify.metaobject.entry.value.ts'].search_count(
                    [('field_id', 'in', stale.ids)])
                _logger.warning(
                    "SHOPIFY METAOBJECT: field(s) %s were removed from definition '%s' in Shopify; "
                    "%s stored value(s) in Odoo were deleted with them.",
                    ', '.join(stale.mapped('key')), definition.shopify_type, value_count)
                stale.unlink()
        return True

    def _prepare_shopify_metaobject_field_vals(self, field_dict, field_type, definition):
        """Task: T9096 - Parse a Shopify fieldDefinition into Odoo values.

        Validations are flattened into explicit columns, mirroring how
        shopify.metafield.mapping.ts stores scale_min / scale_max.
        """
        validations = {v.get('name'): v.get('value') for v in field_dict.get('validations') or []}
        vals = {
            'name': field_dict.get('name'),
            'field_type': field_type,
        }
        if field_type == 'rating':
            vals.update({
                'scale_min': float(validations.get('scale_min') or 0.0),
                'scale_max': float(validations.get('scale_max') or 0.0),
            })
        if 'metaobject_reference' in (field_type or ''):
            referenced_gid = validations.get('metaobject_definition_id')
            if referenced_gid:
                referenced = self.search([
                    ('mk_id', '=', str(extract_numeric_id(referenced_gid))),
                    ('mk_instance_id', '=', definition.mk_instance_id.id),
                ], limit=1)
                vals['ref_definition_id'] = referenced.id or False
        return vals

    def action_fetch_shopify_entries(self):
        """Task: T9096 - Fetch the entries of this definition from Shopify."""
        self.ensure_one()
        if not self.mk_instance_id.enable_metaobject:
            raise MarketplaceException(_(
                "IMPORT METAOBJECT DEFINITION: Cannot fetch entries of metaobject %(definition)s\n"
                "Reason: Metaobject Functionality is turned off for instance (%(instance)s)\n"
                "How to fix:\n"
                "  • Open the instance, go to the Metafields tab and turn on Metaobjects"
            ) % {'definition': self.display_name, 'instance': self.mk_instance_id.name})
        return self.env['shopify.metaobject.entry.ts'].import_shopify_metaobject_entries(self)
