from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

# Labels read the way Shopify words them in its own collection rules.
RELATION_SELECTION = [('GREATER_THAN', 'is greater than'),
                      ('LESS_THAN', 'is less than'),
                      ('EQUALS', 'is equal to'),
                      ('IS_SET', 'is set'),
                      ('IS_NOT_SET', 'is not set'),
                      ('NOT_EQUALS', 'is not equal to'),
                      ('STARTS_WITH', 'starts with'),
                      ('ENDS_WITH', 'ends with'),
                      ('CONTAINS', 'contains'),
                      ('NOT_CONTAINS', 'does not contain'),
                      ('DOES_NOT_CONTAIN', 'does not contain'),
                      ('TAGGED_WITH', 'is tagged with'),
                      ('NOT_TAGGED_WITH', 'is not tagged with'),
                      ('INCLUDES', 'includes')]

# Task: T8887 - How the values of one condition line combine: AND needs every value, OR needs one.
MATCH_TYPE_SELECTION = [('all', 'AND'), ('any', 'OR')]

# Task: T8887 - A condition is an include rule or an exclude rule; both use this model.
CONDITION_KIND_SELECTION = [('inclusion', 'Include'), ('exclusion', 'Exclude')]

# Task: T8887 - Per column: its Shopify key, the kind of value it holds and the relations Shopify accepts.
TEXT_RELATIONS = ('CONTAINS', 'DOES_NOT_CONTAIN', 'ENDS_WITH', 'EQUALS', 'NOT_EQUALS', 'STARTS_WITH')

CONDITION_SPEC = {
    'TITLE': ('productTitle', 'strings', TEXT_RELATIONS),
    'TYPE': ('productType', 'strings', TEXT_RELATIONS),
    'VENDOR': ('productVendor', 'strings', TEXT_RELATIONS),
    'VARIANT_TITLE': ('variantTitle', 'strings', TEXT_RELATIONS),
    'TAG': ('productTag', 'strings', ('TAGGED_WITH', 'NOT_TAGGED_WITH')),
    'PRODUCT_STATUS': ('productStatus', 'status', ('EQUALS', 'NOT_EQUALS')),
    'PRODUCT_CATEGORY_ID': ('productCategory', 'category', ('EQUALS', 'NOT_EQUALS')),
    'VARIANT_PRICE': ('variantPrice', 'money', ('EQUALS', 'GREATER_THAN', 'LESS_THAN', 'NOT_EQUALS')),
    'VARIANT_COMPARE_AT_PRICE': ('variantCompareAtPrice', 'money',
                                 ('EQUALS', 'GREATER_THAN', 'LESS_THAN', 'NOT_EQUALS', 'IS_SET', 'IS_NOT_SET')),
    'VARIANT_WEIGHT': ('variantWeight', 'weight', ('EQUALS', 'GREATER_THAN', 'LESS_THAN', 'NOT_EQUALS')),
    'VARIANT_INVENTORY': ('variantInventory', 'integer', ('EQUALS', 'GREATER_THAN', 'LESS_THAN')),
}

EXCLUSION_SPEC = {
    'TAG': ('productTag', 'strings', ('TAGGED_WITH',)),
    'TYPE': ('productType', 'strings', ('CONTAINS', 'EQUALS')),
    'VENDOR': ('productVendor', 'strings', ('CONTAINS', 'EQUALS')),
    'PRODUCT_CATEGORY_ID': ('productCategory', 'category', ('EQUALS',)),
    'EXCLUDE_COLLECTION': ('collection', 'ids', ()),
}

# The labels the form shows, so an error never names a relation by its Shopify key.
RELATION_LABELS = dict(RELATION_SELECTION)

# Shopify refuses a substring shorter than this: one or two letters would match almost the whole catalogue.
SUBSTRING_RELATIONS = ('CONTAINS', 'DOES_NOT_CONTAIN')
MIN_SUBSTRING_LENGTH = 3

# Shopify keeps only one number for these, so a condition with more values, or a value that is not a number, is refused.
NUMBER_SHAPES = ('money', 'weight', 'integer')
PRODUCT_STATUS_SELECTION = [('ACTIVE', 'Active'), ('ARCHIVED', 'Archived'), ('DRAFT', 'Draft'), ('UNLISTED', 'Unlisted')]
PRODUCT_STATUS_VALUES = tuple(status for status, _label in PRODUCT_STATUS_SELECTION)
TAXONOMY_CATEGORY_PREFIX = 'gid://shopify/TaxonomyCategory/'

# Columns inherited from the ruleSet era that the new model folds into another one.
LEGACY_COLUMN_ALIAS = {
    'tag': 'TAG',
    'PRODUCT_TAXONOMY_NODE_ID': 'PRODUCT_CATEGORY_ID',
    'PRODUCT_CATEGORY_ID_WITH_DESCENDANTS': 'PRODUCT_CATEGORY_ID',
    'IS_PRICE_REDUCED': 'VARIANT_COMPARE_AT_PRICE',
}

# Old relations translated to the new ones; "tag equals X" means "is tagged with X".
RELATION_COMPAT = {
    'productTag': {'EQUALS': 'TAGGED_WITH', 'CONTAINS': 'TAGGED_WITH', 'INCLUDES': 'TAGGED_WITH',
                   'NOT_EQUALS': 'NOT_TAGGED_WITH', 'NOT_CONTAINS': 'NOT_TAGGED_WITH',
                   'DOES_NOT_CONTAIN': 'NOT_TAGGED_WITH'},
    'productTitle': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'productType': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'productVendor': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'variantTitle': {'NOT_CONTAINS': 'DOES_NOT_CONTAIN'},
    'productCategory': {'CONTAINS': 'EQUALS', 'NOT_CONTAINS': 'NOT_EQUALS'},
}


def resolve_condition_spec(column_shopify_name, kind='inclusion'):
    """
    Task: T8887 - Find how a condition column is sent to Shopify.
    Args:
        column_shopify_name (str): Shopify name of the column.
        kind (str): 'inclusion' or 'exclusion'.
    Returns:
        tuple: The column name and its settings, or None when Shopify does not support it.
    """
    column_name = LEGACY_COLUMN_ALIAS.get(column_shopify_name, column_shopify_name)
    spec_table = EXCLUSION_SPEC if kind == 'exclusion' else CONDITION_SPEC
    return column_name, spec_table.get(column_name)


def is_category_column(column_shopify_name, kind='inclusion'):
    """
    Task: T8887 - Check whether a condition column matches product categories.
    Args:
        column_shopify_name (str): Shopify name of the column.
        kind (str): 'inclusion' or 'exclusion'.
    Returns:
        bool: True for a product category column.
    """
    _column_name, condition_spec = resolve_condition_spec(column_shopify_name, kind)
    return bool(condition_spec) and condition_spec[1] == 'category'


def is_status_column(column_shopify_name, kind='inclusion'):
    """
    Task: T8887 - Check whether a condition column matches the product status.
    Args:
        column_shopify_name (str): Shopify name of the column.
        kind (str): 'inclusion' or 'exclusion'.
    Returns:
        bool: True for the product status column.
    """
    _column_name, condition_spec = resolve_condition_spec(column_shopify_name, kind)
    return bool(condition_spec) and condition_spec[1] == 'status'


class ShopifyCollectionCondition(models.Model):
    _name = "shopify.collection.condition.ts"
    _description = "Shopify Collection Condition"

    column_id = fields.Many2one("shopify.collection.condition.column.ts", "Column ID")
    relation = fields.Selection(RELATION_SELECTION, "Relation", help="The relationship between the column choice, and the condition")
    condition = fields.Char("Condition", help="Select products for a smart collection using a condition. "
                                              "Values are either strings or numbers, depending on the relation value.")
    source_id = fields.Many2one("shopify.collection.source.ts", "Source", ondelete='cascade', index=True, help="Source this condition belongs to.")
    shopify_collection_id = fields.Many2one("shopify.collection.ts", "Collection ID", index=True)
    kind = fields.Selection(CONDITION_KIND_SELECTION, "Kind", default='inclusion', required=True, index=True,
                            help="Include adds matching products, Exclude keeps them out.")
    value_ids = fields.One2many("shopify.collection.condition.value.ts", "condition_id", string="Values", help="Values this condition checks.")
    match_type = fields.Selection(MATCH_TYPE_SELECTION, "Match", default='any',
                                  help="AND: a product must match every value. OR: one value is enough.")
    column_shopify_name = fields.Char(related='column_id.shopify_name', string="Column Key", help="Shopify key of the chosen column.")
    category_ids = fields.Many2many("shopify.product.category.ts", "shopify_collection_condition_category_rel", "condition_id", "category_id", string="Categories",
                                    compute='_compute_category_values', inverse='_inverse_category_values', store=True, readonly=False,
                                    help="Shopify product categories to match.")
    include_descendants = fields.Boolean("Include Sub-categories", compute='_compute_category_values', inverse='_inverse_category_values', store=True, readonly=False,
                                         help="Also match products in sub-categories.")
    is_category_condition = fields.Boolean(compute='_compute_is_category_condition', help="Set when this condition matches product categories.")
    status_ids = fields.Many2many("shopify.collection.condition.status.ts", "shopify_collection_condition_status_rel", "condition_id", "status_id", string="Status",
                                  compute='_compute_status_values', inverse='_inverse_status_values', store=True, readonly=False,
                                  help="Product statuses to match, as Shopify names them.")
    is_status_condition = fields.Boolean(compute='_compute_is_status_condition', help="Set when this condition matches the product status.")

    @api.depends('column_id.shopify_name', 'kind')
    def _compute_is_category_condition(self):
        """
        Task: T8887 - Mark the conditions that match product categories.
        """
        for condition in self:
            condition.is_category_condition = is_category_column(condition.column_id.shopify_name, condition.kind)

    @api.depends('column_id.shopify_name', 'kind')
    def _compute_is_status_condition(self):
        """
        Task: T8887 - Mark the conditions that match the product status.
        """
        for condition in self:
            condition.is_status_condition = is_status_column(condition.column_id.shopify_name, condition.kind)

    @api.depends('value_ids.value')
    def _compute_status_values(self):
        """
        Task: T8887 - Fill the status picker from the values of the condition.
            Shopify keeps a list of statuses on one condition, so every value is shown.
        """
        status_names_by_condition = {condition: [(value.value or '').strip().upper() for value in condition.value_ids
                                                 if (value.value or '').strip().upper() in PRODUCT_STATUS_VALUES] for condition in self}
        name_list = list({name for status_name_list in status_names_by_condition.values() for name in status_name_list})
        statuses = self.env['shopify.collection.condition.status.ts'].search(
            [('shopify_name', 'in', name_list)]) if name_list else self.env['shopify.collection.condition.status.ts']
        status_by_name = {status.shopify_name: status.id for status in statuses}
        for condition, status_name_list in status_names_by_condition.items():
            condition.status_ids = [(6, 0, [status_by_name[name] for name in status_name_list if name in status_by_name])]

    def _inverse_status_values(self):
        """
        Task: T8887 - Update the values of a status condition from the statuses picked.
        Returns:
            bool: True.
        """
        for condition in self.filtered('is_status_condition'):
            condition.write({
                'value_ids': [(5, 0, 0)] + [(0, 0, {'sequence': index * 10, 'value': status.shopify_name})
                                            for index, status in enumerate(condition.status_ids)],
                # Legacy mirror, kept the way the import writes it.
                'condition': ", ".join(condition.status_ids.mapped('shopify_name')) or False,
            })
        return True

    @api.depends('value_ids.category_id', 'value_ids.include_descendants')
    def _compute_category_values(self):
        """
        Task: T8887 - Fill the category picker and the sub-categories option from the values of the condition.
        """
        category_values_by_condition = {condition: condition.value_ids.filtered(
            lambda value: (value.category_id or '').startswith(TAXONOMY_CATEGORY_PREFIX)) for condition in self}
        code_list = list({value.category_id[len(TAXONOMY_CATEGORY_PREFIX):]
                          for category_value_records in category_values_by_condition.values() for value in category_value_records})
        categories = self.env['shopify.product.category.ts'].search(
            [('shopify_category_id', 'in', code_list)]) if code_list else self.env['shopify.product.category.ts']
        category_by_code = {category.shopify_category_id: category.id for category in categories}
        for condition, category_value_records in category_values_by_condition.items():
            condition_code_list = [value.category_id[len(TAXONOMY_CATEGORY_PREFIX):] for value in category_value_records]
            condition.category_ids = [(6, 0, [category_by_code[code] for code in condition_code_list if code in category_by_code])]
            condition.include_descendants = bool(category_value_records) and all(category_value_records.mapped('include_descendants'))

    def _inverse_category_values(self):
        """
        Task: T8887 - Update the values of a category condition from the categories picked.
        Returns:
            bool: True.
        Raises:
            MarketplaceException: If a picked category has no Shopify ID.
        """
        for condition in self.filtered('is_category_condition'):
            missing_id = condition.category_ids.filtered(lambda category: not category.shopify_category_id)
            if missing_id:
                raise MarketplaceException(_("Category '%(category)s' has no Shopify ID, so Shopify cannot match on it.\n"
                                             "Fetch the categories from Shopify and pick it again.", category=missing_id[0].complete_name))
            condition.write({
                'value_ids': [(5, 0, 0)] + [(0, 0, {'sequence': index * 10,
                                                    'category_id': TAXONOMY_CATEGORY_PREFIX + category.shopify_category_id,
                                                    'category_name': category.name,
                                                    'include_descendants': condition.include_descendants})
                                            for index, category in enumerate(condition.category_ids)],
                # Legacy mirror, kept the way the import writes it.
                'condition': ", ".join(condition.category_ids.mapped('name')) or False,
            })
        return True

    def sync_values_from_condition(self):
        """
        Task: T8887 - Create the value lines from what was typed in the Values field.
            Values are separated by commas.
        Returns:
            bool: True.
        """
        for condition in self:
            value_vals_list = []
            for index, token in enumerate((condition.condition or '').split(',')):
                token = token.strip()
                if not token:
                    continue
                key = 'category_id' if token.startswith('gid://') else 'value'
                value_vals_list.append((0, 0, {'sequence': index * 10, key: token}))
            condition.value_ids = [(5, 0, 0)] + value_vals_list
        return True

    def sync_collection_from_source(self):
        """
        Task: T8887 - Set the collection of the condition to the collection of its source.
        Returns:
            bool: True.
        """
        for condition in self.filtered('source_id'):
            if condition.shopify_collection_id != condition.source_id.collection_id:
                condition.shopify_collection_id = condition.source_id.collection_id
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """
        Task: T8887 - Create conditions and fill their value lines from the typed values.
        Args:
            vals_list (list): Values of the new conditions.
        Returns:
            recordset: The new conditions.
        """
        conditions = super().create(vals_list)
        conditions.sync_collection_from_source()
        # Build the value lines from the typed values, unless they were given or picked.
        for condition, vals in zip(conditions, vals_list):
            if (vals.get('condition') and not vals.get('value_ids')
                    and not (vals.get('category_ids') and condition.is_category_condition)
                    and not (vals.get('status_ids') and condition.is_status_condition)):
                condition.sync_values_from_condition()
        return conditions

    def write(self, vals):
        """
        Task: T8887 - Update conditions and keep their value lines in line with the typed values or picked categories.
        Args:
            vals (dict): Values to update.
        Returns:
            bool: True.
        """
        if 'column_id' in vals and 'value_ids' not in vals:
            # When the column changes to a category, the old typed values are cleared first.
            new_column = self.env['shopify.collection.condition.column.ts'].browse(vals['column_id'])
            self.filtered(lambda condition: not condition.is_category_condition
                          and is_category_column(new_column.shopify_name, condition.kind)).value_ids = [(5, 0, 0)]
        res = super().write(vals)
        if 'source_id' in vals:
            self.sync_collection_from_source()
        if 'condition' in vals and 'value_ids' not in vals:
            # A category picked alongside wins over the text, which then only mirrors it.
            picked_condition_ids = self.filtered('is_category_condition') if 'category_ids' in vals else self.browse()
            picked_condition_ids |= self.filtered('is_status_condition') if 'status_ids' in vals else self.browse()
            (self - picked_condition_ids).sync_values_from_condition()
        return res

    @api.constrains('column_id', 'relation', 'value_ids', 'kind')
    def _check_condition_is_exportable(self):
        """
        Task: T8887 - Check, when a condition is saved, that Shopify can accept it.
            Checks the relation, the number of values, numbers, product statuses and categories.
        Raises:
            MarketplaceException: With what to fix.
        """
        for condition in self:
            if not condition.column_id:
                continue
            column_label = condition.column_id.name
            condition_spec = resolve_condition_spec(condition.column_id.shopify_name, condition.kind)[1]
            if not condition_spec:
                raise MarketplaceException(_("Condition '%(column)s' cannot be sent to Shopify. Pick another one.", column=column_label))
            input_key, shape, allowed_relations = condition_spec

            if allowed_relations:
                allowed = ", ".join(sorted(RELATION_LABELS.get(relation, relation) for relation in allowed_relations))
                if not condition.relation:
                    # Shopify declares these relations non-null; an empty one is rejected outright.
                    raise MarketplaceException(_("'%(column)s' needs a relation.\nAllowed: %(allowed)s", column=column_label,
                                                 allowed=allowed))
                # Relations stored under the old shared list still count: they are translated on export.
                translated = RELATION_COMPAT.get(input_key, {}).get(condition.relation, condition.relation)
                if translated not in allowed_relations:
                    raise MarketplaceException(_("'%(column)s' does not support the relation '%(relation)s' on Shopify.\n"
                                                 "Allowed: %(allowed)s", column=column_label,
                                                 relation=RELATION_LABELS.get(condition.relation, condition.relation), allowed=allowed))

            value_records = condition.value_ids
            if not value_records:
                continue  # an empty line is still being filled in; export reports it

            if RELATION_COMPAT.get(input_key, {}).get(condition.relation, condition.relation) in SUBSTRING_RELATIONS:
                for value in value_records:
                    if 0 < len((value.value or '').strip()) < MIN_SUBSTRING_LENGTH:
                        raise MarketplaceException(_("'%(column)s' searches for a part of the text, so '%(value)s' is too short.\n"
                                                     "Use at least %(count)s characters.", column=column_label,
                                                     value=(value.value or '').strip(), count=MIN_SUBSTRING_LENGTH))

            if shape in NUMBER_SHAPES and len(value_records) > 1:
                raise MarketplaceException(_("'%(column)s' holds a single value on Shopify, but these were entered: %(values)s\n"
                                             "Keep one value, or add a separate condition for each.", column=column_label,
                                             values=", ".join(filter(None, value_records.mapped('display_value')))))

            if shape in NUMBER_SHAPES:
                for value in value_records:
                    try:
                        float((value.value or '').strip())
                    except (TypeError, ValueError):
                        raise MarketplaceException(_("'%(column)s' expects a number, but holds '%(value)s'.", column=column_label,
                                                     value=value.value or ''))

            if shape == 'status':
                for value in value_records:
                    if (value.value or '').strip().upper() not in PRODUCT_STATUS_VALUES:
                        raise MarketplaceException(_("'%(column)s' accepts only %(allowed)s, but holds '%(value)s'.", column=column_label,
                                                     allowed=", ".join(label for _status, label in PRODUCT_STATUS_SELECTION),
                                                     value=value.value or ''))

            # Categories and excluded collections need their Shopify ID, not a name.
            expected_prefix = {'category': TAXONOMY_CATEGORY_PREFIX, 'ids': 'gid://shopify/Collection/'}.get(shape)
            if expected_prefix:
                for value in value_records:
                    if not (value.category_id or '').startswith(expected_prefix):
                        raise MarketplaceException(_("'%(column)s' needs a Shopify ID starting with %(prefix)s, not '%(value)s'.") % {
                            'column': column_label, 'prefix': expected_prefix, 'value': value.category_id or value.value or ''})
        return True

    @api.onchange('column_id', 'kind')
    def _onchange_column_id_reset_relation(self):
        """
        Task: T8887 - Clear the relation and values that do not fit the newly chosen column.
        """
        for condition in self:
            if not condition.column_id:
                continue
            _column_name, condition_spec = resolve_condition_spec(condition.column_id.shopify_name, condition.kind)
            if not condition_spec:
                continue
            input_key, shape, allowed_relations = condition_spec
            # Category and status conditions are picked and the others typed, so clear what does not apply.
            if shape in ('category', 'status'):
                condition.condition = False
            if shape != 'category':
                condition.category_ids = [(5, 0, 0)]
                condition.include_descendants = False
            if shape != 'status':
                condition.status_ids = [(5, 0, 0)]
            if not allowed_relations:
                # "in collection" takes neither a relation nor a match type.
                condition.relation = False
                condition.match_type = 'any'
            elif condition.relation:
                translated = RELATION_COMPAT.get(input_key, {}).get(condition.relation, condition.relation)
                if translated not in allowed_relations:
                    condition.relation = False

class ShopifyCollectionConditionColumn(models.Model):
    _name = "shopify.collection.condition.column.ts"
    _description = "Shopify Collection Condition Column"

    name = fields.Char("Name", required=True)
    shopify_name = fields.Char("Shopify Name", required=True)


class ShopifyCollectionConditionStatus(models.Model):
    _name = "shopify.collection.condition.status.ts"
    _description = "Shopify Collection Condition Status"

    name = fields.Char("Name", required=True)
    shopify_name = fields.Char("Shopify Name", required=True)


class ShopifyCollectionConditionValue(models.Model):
    _name = "shopify.collection.condition.value.ts"
    _description = "Shopify Collection Condition Value"
    _order = "sequence, id"

    sequence = fields.Integer("Sequence", default=10, help="Order of this value in the condition.")
    condition_id = fields.Many2one("shopify.collection.condition.ts", "Condition", ondelete='cascade', required=True, index=True, help="Condition this value belongs to.")
    value = fields.Char("Value", help="Text or number to match, such as a tag or a price.")
    category_id = fields.Char("Reference ID", help="Shopify ID of the category or collection to match.")
    category_name = fields.Char("Reference Name", help="Name of the category or collection to match.")
    unit = fields.Char("Unit", help="Currency for prices, or unit for weight.")
    include_descendants = fields.Boolean("Include Sub categories", help="Also match products in sub categories.")
    display_value = fields.Char("Display", compute='_compute_display_value', store=True, help="Value as shown in the list.")

    @api.depends('value', 'category_id', 'category_name', 'unit')
    def _compute_display_value(self):
        """
        Task: T8887 - Compute how a value is shown in the list, with its currency or unit.
        """
        for record in self:
            base = record.value or record.category_name or record.category_id or ''
            record.display_value = f"{base} {record.unit}" if base and record.unit else base
