import json
from datetime import datetime

from odoo import models, fields, api, _
from odoo.addons.shopify.models.misc import (extract_numeric_id, _convert_shopify_rich_text_to_html, convert_html_to_shopify_rich_text, convert_shopify_metafield_measurement)
from odoo.tools import html2plaintext

WEIGHT_UNITS = [('GRAMS', 'Grams'), ('KILOGRAMS', 'Kilograms'), ('POUNDS', 'Pounds'), ('OUNCES', 'Ounces'), ]
VOLUME_UNITS = [
    ('MILLILITERS', 'Milliliters'), ('CENTILITERS', 'Centiliters'), ('LITERS', 'Liters'),
    ('CUBIC_METERS', 'Cubic meters'), ('FLUID_OUNCES', 'Fluid ounces'), ('PINTS', 'Pints'),
    ('QUARTS', 'Quarts'), ('GALLONS', 'Gallons'),
    ('IMPERIAL_FLUID_OUNCES', 'Imperial fluid ounces'), ('IMPERIAL_PINTS', 'Imperial pints'),
    ('IMPERIAL_QUARTS', 'Imperial quarts'), ('IMPERIAL_GALLONS', 'Imperial gallons'),
]
MEASUREMENT_UNITS = WEIGHT_UNITS + VOLUME_UNITS
TEXT_TYPES = ('single_line_text_field', 'url', 'color', 'id')
REFERENCE_BUCKETS = {
    'product': ('mk.listing', 'product_tmpl_id'),
    'variant': ('mk.listing.item', 'product_id'),
    'entry': ('shopify.metaobject.entry.ts', None),
}
REFERENCE_BUCKET_BY_TYPE = {
    'product_reference': 'product',
    'variant_reference': 'variant',
    'metaobject_reference': 'entry',
}
REFERENCE_COLUMNS = {
    'product': ('val_product_id', 'val_product_ids'),
    'variant': ('val_variant_id', 'val_variant_ids'),
    'entry': ('val_entry_id', 'val_entry_ids'),
}
LONG_TEXT_TYPES = ('multi_line_text_field', 'json')


class ShopifyMetaobjectEntryValue(models.Model):
    _name = 'shopify.metaobject.entry.value.ts'
    _description = 'Shopify Metaobject Entry Value'
    _order = 'entry_id, id'
    _rec_name = 'key'

    entry_id = fields.Many2one('shopify.metaobject.entry.ts', string="Entry", required=True, ondelete='cascade',
                               help="Metaobject entry this value belongs to.")
    field_id = fields.Many2one('shopify.metaobject.field.ts', string="Field", required=True, ondelete='cascade',
                               help="Field definition this value fills in.")

    mk_instance_id = fields.Many2one(related='entry_id.mk_instance_id', store=True, string="Instance")
    key = fields.Char(related='field_id.key', store=True, string="Key")
    field_type = fields.Char(related='field_id.field_type', store=True, string="Type")
    is_supported = fields.Boolean(related='field_id.is_supported', store=True, string="Editable")

    # ------------------------------------------------------------------
    # TYPED INPUTS - the only columns the user ever edits.
    # ------------------------------------------------------------------
    val_char = fields.Char(string="Single-Line Value", help="single_line_text_field, url, color, id, and the URL part of link.")
    val_text = fields.Text(string="Text Value", help="multi_line_text_field and json.")
    val_html = fields.Html(string="Rich Text Value", sanitize=False, help="rich_text_field.")
    val_int = fields.Integer(string="Integer Value", help="number_integer.")
    val_float = fields.Float(string="Decimal Value", help="number_decimal, rating, weight, volume, money.")
    val_bool = fields.Boolean(string="Boolean Value", help="boolean.")
    val_date = fields.Date(string="Date Value", help="date.")
    val_datetime = fields.Datetime(string="Date & Time Value", help="date_time.")

    # composite companions
    val_link_text = fields.Char(string="Link Text", help="Text part of a link value.")
    # Two selections rather than one: Odoo cannot filter Selection options per record, and a
    # single combined list let a weight unit be picked on a volume field.
    val_weight_unit = fields.Selection(WEIGHT_UNITS, string="Shopify Weight Unit",
                                       help="Unit Shopify stores this weight in. The value beside it is held in "
                                            "Odoo's own unit and converted back to this one on push.")
    val_volume_unit = fields.Selection(VOLUME_UNITS, string="Shopify Volume Unit",
                                       help="Unit Shopify stores this volume in. The value beside it is held in "
                                            "Odoo's own unit and converted back to this one on push.")
    odoo_uom_label = fields.Char(string="Odoo Unit", compute='_compute_shopify_odoo_uom_label',
                                 help="Unit the value beside it is expressed in, taken from Odoo's weight/volume "
                                      "settings. Not stored.")

    # references - real Odoo records, resolved to Shopify GIDs on export
    val_product_id = fields.Many2one('product.template', string="Product", help="product_reference.")
    val_variant_id = fields.Many2one('product.product', string="Variant", help="variant_reference.")
    val_entry_id = fields.Many2one('shopify.metaobject.entry.ts', string="Metaobject Entry",
                                   domain="[('definition_id', '=', ref_definition_id)]",
                                   help="metaobject_reference (nested metaobject).", ondelete='set null')
    val_product_ids = fields.Many2many('product.template', 'shopify_mo_value_product_rel', 'value_id', 'product_id',
                                       string="Products", help="list.product_reference.")
    val_variant_ids = fields.Many2many('product.product', 'shopify_mo_value_variant_rel', 'value_id', 'variant_id',
                                       string="Variants", help="list.variant_reference.")
    val_entry_ids = fields.Many2many('shopify.metaobject.entry.ts', 'shopify_mo_value_entry_rel', 'value_id',
                                     'ref_entry_id', string="Metaobject Entries",
                                     domain="[('definition_id', '=', ref_definition_id)]",
                                     help="list.metaobject_reference.")

    ref_definition_id = fields.Many2one(related='field_id.ref_definition_id', store=True,
                                        string="Referenced Definition",
                                        help="For metaobject_reference fields: which definition the referenced "
                                             "entries must belong to. Restricts the picker.")
    scale_min = fields.Float(related='field_id.scale_min', string="Rating Minimum Scale")
    scale_max = fields.Float(related='field_id.scale_max', string="Rating Maximum Scale")

    display_value = fields.Char(string="Value", compute='_compute_shopify_display_value',
                                help="Human readable form of the value, shown in the list. "
                                     "Not stored: it is derived from the typed column on read.")

    # _create_or_update_shopify_metaobject_entries looks up an existing value row by key before
    # creating one, so it never produces a duplicate on its own. This constraint guards the
    # case that check can't cover: the same entry being imported twice at once (e.g. a
    # scheduled sync and a manual re-import overlapping).
    _uniq_field_per_entry = models.Constraint(
        "UNIQUE(entry_id, field_id)",
        "This field already has a value on the entry.")

    # ==================================================================
    # DISPLAY : typed columns -> one readable line
    # ==================================================================
    @api.depends('field_type', 'val_char', 'val_text', 'val_html', 'val_int', 'val_float', 'val_bool',
                 'val_date', 'val_datetime', 'val_link_text', 'val_weight_unit', 'val_volume_unit',
                 'val_product_id', 'val_variant_id', 'val_entry_id',
                 'val_product_ids', 'val_variant_ids', 'val_entry_ids', 'scale_max')
    def _compute_shopify_display_value(self):
        """Task: T9096 - One readable line per value, whatever the Shopify type.

        Only used for the list column: the merchant edits the typed column itself in the
        row dialog, so this never has to round-trip.
        """
        for record in self:
            record.display_value = record._to_shopify_display_value()

    @property
    def _shopify_unit(self):
        """Task: T9096 - Shopify unit code for this row, from whichever measurement column applies."""
        self.ensure_one()
        if self.field_type == 'weight':
            return self.val_weight_unit
        if self.field_type == 'volume':
            return self.val_volume_unit
        return False

    @api.depends('field_type')
    def _compute_shopify_odoo_uom_label(self):
        for record in self:
            uom = record._shopify_odoo_measurement_uom(record.field_type) \
                if record.field_type in ('weight', 'volume') else False
            record.odoo_uom_label = uom.name if uom else ''

    def _shopify_odoo_measurement_uom(self, m_type):
        """Task: T9096 - Odoo UoM a converted weight/volume is expressed in.

        Mirrors the target chosen by misc.convert_shopify_metafield_measurement so the
        displayed unit always matches the stored number.
        """
        param = self.env['ir.config_parameter'].sudo()
        if m_type == 'weight':
            xml_id = 'uom.product_uom_lb' if param.get_param('product.weight_in_lbs') == '1' \
                else 'uom.product_uom_kgm'
        else:
            xml_id = 'uom.product_uom_cubic_foot' if param.get_param('product.volume_in_cubic_feet') == '1' \
                else 'uom.product_uom_cubic_meter'
        return self.env.ref(xml_id, raise_if_not_found=False)

    def _to_shopify_display_value(self):
        """Task: T9096 - Render this value as a short human readable string."""
        self.ensure_one()
        field_type = self.field_type or ''

        if not self.is_supported:
            return (self.val_text or '').strip()[:120]

        if field_type == 'product_reference':
            return self.val_product_id.display_name or ''
        if field_type == 'variant_reference':
            return self.val_variant_id.display_name or ''
        if field_type == 'metaobject_reference':
            return self.val_entry_id.display_name_ts or ''
        if field_type == 'list.product_reference':
            return ', '.join(self.val_product_ids.mapped('display_name'))
        if field_type == 'list.variant_reference':
            return ', '.join(self.val_variant_ids.mapped('display_name'))
        if field_type == 'list.metaobject_reference':
            return ', '.join(e.display_name_ts or e.handle or '' for e in self.val_entry_ids)

        if field_type == 'link':
            if not self.val_char:
                return ''
            return f"{self.val_link_text} \u2192 {self.val_char}" if self.val_link_text else self.val_char
        if field_type in ('weight', 'volume'):
            # val_float is in Odoo's configured UoM after conversion, while the Shopify unit
            # is what we send back. Naming the Shopify unit here would read "2.0 Grams" for a
            # value that is actually 2 kg, so name Odoo's unit instead.
            odoo_uom = self._shopify_odoo_measurement_uom(field_type)
            return f"{self.val_float} {odoo_uom.name}".strip() if odoo_uom else str(self.val_float)
        if field_type == 'money':
            return f"{self.val_float} {self.mk_instance_id.pricelist_id.currency_id.symbol or ''}".strip()
        if field_type == 'rating':
            return f"{self.val_float} / {self.scale_max}" if self.scale_max else str(self.val_float)
        if field_type == 'rich_text_field':
            return (html2plaintext(self.val_html) or '').strip()[:120] if self.val_html else ''

        if field_type == 'boolean':
            return _("Yes") if self.val_bool else _("No")
        if field_type == 'number_integer':
            return str(self.val_int)
        if field_type == 'number_decimal':
            return str(self.val_float)
        if field_type == 'date':
            return self.val_date.strftime("%Y-%m-%d") if self.val_date else ''
        if field_type == 'date_time':
            return self.val_datetime.strftime("%Y-%m-%d %H:%M") if self.val_datetime else ''
        if field_type in LONG_TEXT_TYPES:
            return (self.val_text or '').strip()[:120]
        return self.val_char or ''

    # ==================================================================
    # EXPORT : typed columns -> Shopify string
    # ==================================================================
    def _to_shopify_value(self, mk_log_line_dict=None):
        """Task: T9096 - Build the exact string Shopify expects for this field type.

        Args:
            mk_log_line_dict (dict, optional): Dictionary to collect log messages.

        Returns:
            str | bool: Shopify value string, or False when there is nothing to send.
        """
        self.ensure_one()
        field_type = self.field_type or ''

        # A type the connector cannot convert is never sent back.
        if not self.is_supported:
            return False

        # -- references -------------------------------------------------
        if field_type == 'product_reference':
            return self._shopify_gid_from_listing(self.val_product_id, 'Product')
        if field_type == 'variant_reference':
            return self._shopify_gid_from_listing(self.val_variant_id, 'ProductVariant')
        if field_type == 'metaobject_reference':
            return self._shopify_gid_from_entry(self.val_entry_id)
        if field_type == 'list.product_reference':
            return json.dumps([self._shopify_gid_from_listing(p, 'Product') for p in self.val_product_ids])
        if field_type == 'list.variant_reference':
            return json.dumps([self._shopify_gid_from_listing(v, 'ProductVariant') for v in self.val_variant_ids])
        if field_type == 'list.metaobject_reference':
            return json.dumps([self._shopify_gid_from_entry(e) for e in self.val_entry_ids])

        # -- composites -------------------------------------------------
        if field_type == 'link':
            if not self.val_char:
                if self.val_link_text and mk_log_line_dict is not None:
                    log_message = _(
                        "UPDATE METAOBJECT ENTRY: Skipped the value of field %(field)s of entry %(entry)s (%(definition)s) for instance (%(instance)s)\n"
                        "Reason: the link has text (%(text)s) but no URL\n"
                        "How to fix:\n"
                        "  • Go to Marketplaces > Shopify > Catalogs > Metaobject Entries, open the entry, add the URL of %(field)s in the Values tab or clear the link text, then click Sync to Shopify"
                    ) % {
                        'field': self.field_id.name or self.key,
                        'entry': self.entry_id._shopify_entry_label(),
                        'definition': self.entry_id.definition_id.name,
                        'instance': self.mk_instance_id.name,
                        'text': self.val_link_text,
                    }
                    mk_log_line_dict['error'].append({'log_message': log_message})
                return False
            return json.dumps({"url": self.val_char, "text": self.val_link_text or ""})

        if field_type in ('weight', 'volume'):
            shopify_unit = self._shopify_unit
            if not shopify_unit:
                if mk_log_line_dict is not None:
                    log_message = _(
                        "UPDATE METAOBJECT ENTRY: Skipped the value of field %(field)s of entry %(entry)s (%(definition)s) for instance (%(instance)s)\n"
                        "Reason: no unit is chosen for this %(kind)s\n"
                        "How to fix:\n"
                        "  • Go to Marketplaces > Shopify > Catalogs > Metaobject Entries, open the entry, choose the unit next to %(field)s in the Values tab, then click Sync to Shopify"
                    ) % {
                        'kind': field_type,
                        'field': self.field_id.name or self.key,
                        'entry': self.entry_id._shopify_entry_label(),
                        'definition': self.entry_id.definition_id.name,
                        'instance': self.mk_instance_id.name,
                    }
                    mk_log_line_dict['error'].append({'log_message': log_message})
                return False
            converted_value, shopify_unit = self.mk_instance_id.update_measurement_metafield_to_shopify(
                m_type=field_type, value=self.val_float, unit=shopify_unit)
            return json.dumps({"value": converted_value, "unit": shopify_unit or ""})

        if field_type == 'money':
            currency = self.mk_instance_id.pricelist_id.currency_id
            if not currency:
                if mk_log_line_dict is not None:
                    log_message = _(
                        "UPDATE METAOBJECT ENTRY: Skipped the value of field %(field)s of entry %(entry)s (%(definition)s) for instance (%(instance)s)\n"
                        "Reason: the instance pricelist has no currency\n"
                        "How to fix:\n"
                        "  • Go to Marketplaces > Configuration > Instance, open the instance, set a Pricelist that has a currency, then click Sync to Shopify on the entry"
                    ) % {
                        'field': self.field_id.name or self.key,
                        'entry': self.entry_id._shopify_entry_label(),
                        'definition': self.entry_id.definition_id.name,
                        'instance': self.mk_instance_id.name,
                    }
                    mk_log_line_dict['error'].append({'log_message': log_message})
                return False
            return json.dumps({"amount": str(self.val_float), "currency_code": currency.name or ""})

        if field_type == 'rating':
            return json.dumps({"value": str(self.val_float),
                               "scale_min": self.scale_min, "scale_max": self.scale_max})

        if field_type == 'rich_text_field':
            return convert_html_to_shopify_rich_text(self.val_html) if self.val_html else False

        # -- scalars ----------------------------------------------------
        if field_type == 'boolean':
            return "true" if self.val_bool else "false"
        if field_type == 'number_integer':
            return str(self.val_int)
        if field_type == 'number_decimal':
            return str(self.val_float)
        if field_type == 'date':
            return self.val_date.strftime("%Y-%m-%d") if self.val_date else False
        if field_type == 'date_time':
            return self.val_datetime.strftime("%Y-%m-%dT%H:%M:%S") if self.val_datetime else False
        if field_type in LONG_TEXT_TYPES:
            return self.val_text or False
        return self.val_char or False

    def _shopify_listing_mk_id(self, record, resource):
        """Task: T9096 - Shopify id of a product/variant for this instance, or False when not exported."""
        if not record:
            return False
        relational_field = 'mk_listing_ids' if resource == 'Product' else 'mk_listing_item_ids'
        listing = getattr(record, relational_field).filtered(
            lambda l: l.mk_instance_id.id == self.mk_instance_id.id and l.mk_id)
        return listing[0].mk_id if listing else False

    def _shopify_gid_from_listing(self, record, resource):
        """Task: T9096 - Resolve an Odoo product/variant to its Shopify GID, or False.

        Never raises: an unresolved reference is reported by
        _unresolvable_reference_reason and the field is skipped, exactly as
        prepare_shopify_reference_value_for_update does for metafields.
        """
        mk_id = self._shopify_listing_mk_id(record, resource)
        return f"gid://shopify/{resource}/{mk_id}" if mk_id else False

    def _shopify_gid_from_entry(self, entry):
        """Task: T9096 - Resolve a nested metaobject entry to its Shopify GID, or False."""
        if not entry or not entry.mk_id:
            return False
        return f"gid://shopify/Metaobject/{entry.mk_id}"

    # TODO: need to remove this method... ( instead of remove need to handle correctly from update)
    def _export_skip_reason(self):
        """Log message when this field cannot be sent to Shopify, else False.

        Returns False when the field is fine to send. Mirrors the metafield behaviour:
        the field is skipped with an explanation and the rest of the entry still exports,
        rather than aborting the whole push.
        """
        self.ensure_one()
        field_type = self.field_type or ''

        # Unsupported types are omitted by design, not an error worth logging every push.
        if not self.is_supported:
            return False

        if '_reference' not in field_type:
            return False

        missing, ref_label = [], ''
        if field_type == 'product_reference':
            ref_label = _("product")
            if self.val_product_id and not self._shopify_listing_mk_id(self.val_product_id, 'Product'):
                missing = [self.val_product_id.display_name]
        elif field_type == 'list.product_reference':
            ref_label = _("product")
            missing = [p.display_name for p in self.val_product_ids
                       if not self._shopify_listing_mk_id(p, 'Product')]
        elif field_type == 'variant_reference':
            ref_label = _("variant")
            if self.val_variant_id and not self._shopify_listing_mk_id(self.val_variant_id, 'ProductVariant'):
                missing = [self.val_variant_id.display_name]
        elif field_type == 'list.variant_reference':
            ref_label = _("variant")
            missing = [v.display_name for v in self.val_variant_ids
                       if not self._shopify_listing_mk_id(v, 'ProductVariant')]
        elif field_type == 'metaobject_reference':
            ref_label = _("metaobject entry")
            if self.val_entry_id and not self.val_entry_id.mk_id:
                missing = [self.val_entry_id._shopify_entry_label()]
        elif field_type == 'list.metaobject_reference':
            ref_label = _("metaobject entry")
            missing = [e._shopify_entry_label() for e in self.val_entry_ids if not e.mk_id]

        if not missing:
            return False

        if field_type.endswith('metaobject_reference'):
            fix = _("Go to Marketplaces > Shopify > Catalogs > Metaobject Entries, open each entry above and click Sync to Shopify, then sync this entry again")
        else:
            fix = _("Sync these %s(s) to Shopify, then sync this entry again") % ref_label

        return _(
            "UPDATE METAOBJECT ENTRY: Skipped the value of field %(field)s of entry %(entry)s (%(definition)s) for instance (%(instance)s)\n"
            "Reason: the following linked %(ref_label)s(s) are not synced to Shopify yet:\n"
            "%(missing)s\n"
            "How to fix:\n"
            "  \u2022 %(fix)s"
        ) % {
            'field': self.field_id.name or self.key,
            'entry': self.entry_id._shopify_entry_label(),
            'definition': self.entry_id.definition_id.name,
            'instance': self.mk_instance_id.name,
            'ref_label': ref_label,
            'missing': "  \u2022 " + "\n  \u2022 ".join(missing),
            'fix': fix,
        }

    # ==================================================================
    # IMPORT : Shopify string -> typed columns
    # ==================================================================
    def _apply_shopify_value(self, raw, reference_cache=None):
        """Task: T9096 - Populate the typed columns from a raw Shopify value string.

        Args:
            raw (str): Value exactly as returned by Shopify.
            reference_cache (dict, optional): Pre-resolved reference ids, see
                shopify.metaobject.entry.ts._build_shopify_reference_cache. Avoids one search
                per reference value on large imports.
        Returns:
            bool: True once written.
        """
        self.ensure_one()
        vals = self._prepare_shopify_odoo_value_vals(raw, reference_cache=reference_cache)
        if vals:
            self.write(vals)
        return True

    def _resolve_shopify_reference_ids(self, bucket, mk_ids, reference_cache):
        """Task: T9096 - Resolve Shopify ids to Odoo ids, using the batch cache when available.

        Args:
            bucket (str): One of 'product', 'variant', 'entry'.
            mk_ids (list): Shopify numeric ids as strings.
            reference_cache (dict | None): Pre-resolved mapping per bucket.
        Returns:
            list: Odoo record ids, in the order the Shopify ids were given.
        """
        if not mk_ids:
            return []
        if reference_cache is not None and bucket in reference_cache:
            cached = reference_cache[bucket]
            return [cached[mk_id] for mk_id in mk_ids if cached.get(mk_id)]

        model_name, target = REFERENCE_BUCKETS[bucket]
        records = self.env[model_name].search([
            ('mk_id', 'in', mk_ids), ('mk_instance_id', '=', self.mk_instance_id.id)])
        by_mk_id = {r.mk_id: (r if target is None else r[target]).id for r in records}
        return [by_mk_id[mk_id] for mk_id in mk_ids if by_mk_id.get(mk_id)]

    def _prepare_shopify_odoo_value_vals(self, raw, reference_cache=None):
        """Task: T9096 - Convert a raw Shopify value into typed Odoo values.

        Returns:
            dict: Values for the matching val_* column(s). Empty when unconvertible.
        """
        self.ensure_one()
        field_type = self.field_type or ''
        if raw in (None, ''):
            return self._blank_shopify_value_vals()

        # Unsupported type: keep Shopify's raw string verbatim so it is visible in Odoo.
        if not self.is_supported:
            return {'val_text': raw}

        parsed = self._safe_shopify_json_loads(raw)

        if '_reference' in field_type:
            bucket = REFERENCE_BUCKET_BY_TYPE.get(field_type.removeprefix('list.'))
            if bucket:
                is_list = field_type.startswith('list.')
                gid_list = (parsed or []) if is_list else [raw]
                mk_ids = [str(extract_numeric_id(gid)) for gid in gid_list if gid]
                resolved = self._resolve_shopify_reference_ids(bucket, mk_ids, reference_cache)
                column = REFERENCE_COLUMNS[bucket][1 if is_list else 0]
                if is_list:
                    return {column: [fields.Command.set(resolved)]}
                return {column: resolved[0] if resolved else False}

        if field_type == 'link':
            return {'val_char': (parsed or {}).get('url'), 'val_link_text': (parsed or {}).get('text')}
        if field_type in ('weight', 'volume'):
            # Convert into Odoo's configured UoM, exactly as import_shopify_measurement_metafield
            shopify_unit = (parsed or {}).get('unit') or False
            if not shopify_unit:
                raise ValueError(_("Shopify did not send a unit for this %s value.") % field_type)
            converted = convert_shopify_metafield_measurement(
                env=self.env, m_type=field_type, value=float((parsed or {}).get('value') or 0.0),
                shopify_unit=shopify_unit, reverse=False)
            unit_column = 'val_weight_unit' if field_type == 'weight' else 'val_volume_unit'
            return {'val_float': converted, unit_column: shopify_unit}
        if field_type == 'money':
            return {'val_float': float((parsed or {}).get('amount') or 0.0)}
        if field_type == 'rating':
            return {'val_float': float((parsed or {}).get('value') or 0.0)}
        if field_type == 'rich_text_field':
            return {'val_html': _convert_shopify_rich_text_to_html(parsed) if parsed else False}

        if field_type == 'boolean':
            return {'val_bool': str(raw).strip().lower() == 'true'}
        if field_type == 'number_integer':
            return {'val_int': int(raw)}
        if field_type == 'number_decimal':
            return {'val_float': float(raw)}
        if field_type == 'date':
            return {'val_date': str(raw)[:10]}
        if field_type == 'date_time':
            return {'val_datetime': datetime.strptime(str(raw).replace('+00:00', 'Z'), "%Y-%m-%dT%H:%M:%SZ")}
        if field_type in LONG_TEXT_TYPES:
            return {'val_text': raw}
        return {'val_char': raw}

    def _blank_shopify_value_vals(self):
        """Task: T9096 - Clear every typed column, used when Shopify returns an empty value."""
        self.ensure_one()
        return {
            'val_char': False, 'val_text': False, 'val_html': False, 'val_int': 0, 'val_float': 0.0,
            'val_bool': False, 'val_date': False, 'val_datetime': False, 'val_link_text': False,
            'val_weight_unit': False, 'val_volume_unit': False, 'val_product_id': False, 'val_variant_id': False,
            'val_entry_id': False, 'val_product_ids': [fields.Command.clear()],
            'val_variant_ids': [fields.Command.clear()], 'val_entry_ids': [fields.Command.clear()],
        }

    def _shopify_reference_buckets(self):
        """Task: T9096 - Expose the bucket -> (model, target field) map for batch resolution."""
        return REFERENCE_BUCKETS

    def _shopify_reference_bucket_for_type(self, field_type):
        """Task: T9096 - Return the reference bucket for a Shopify field type, list or not."""
        return REFERENCE_BUCKET_BY_TYPE.get((field_type or '').removeprefix('list.'))

    def _safe_shopify_json_loads(self, raw):
        """Task: T9096 - Parse a JSON string, returning None instead of raising."""
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
