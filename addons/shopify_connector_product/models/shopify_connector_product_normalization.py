"""Shared Shopify product-shape normalization.

Shopify represents a one-variant product with the transport-only option
``Title / Default Title``.  Odoo represents the same product by having no
business attribute at all.  Keeping this rule in one small, dependency-free
module prevents import, preview, comparison, and mutation builders from
disagreeing about whether a singleton changed shape.
"""


DEFAULT_OPTION_NAME = 'title'
DEFAULT_OPTION_VALUE = 'default title'


def normalize_option_specs(options):
    """Return canonical business options, sorted by Shopify position.

    The conventional Shopify singleton is transport metadata, not an Odoo
    attribute.  It therefore normalizes to an empty option list.  The returned
    objects intentionally contain only the fields consumed by the connector.
    """
    normalized = []
    for option in options or []:
        option = option if isinstance(option, dict) else {}
        values = []
        raw_values = option.get('values')
        if raw_values is None:
            raw_values = [
                value.get('name')
                for value in (option.get('optionValues') or [])
                if isinstance(value, dict) and value.get('name') is not None
            ]
        for value in raw_values or []:
            if isinstance(value, dict):
                value = value.get('name')
            if value is not None:
                values.append(value)
        normalized.append({
            'name': option.get('name'),
            'position': option.get('position') or 0,
            'values': values,
        })
    normalized.sort(key=lambda option: option['position'])
    if is_singleton_options(normalized):
        return []
    return normalized


def is_singleton_options(options):
    """Whether an option list is Shopify's conventional singleton shape."""
    if len(options or []) != 1:
        return not options
    option = options[0] or {}
    name = (option.get('name') or '').strip().lower()
    values = [
        (value or '').strip().lower()
        for value in option.get('values') or []
    ]
    return name == DEFAULT_OPTION_NAME and values == [DEFAULT_OPTION_VALUE]


def normalize_selected_options(selected_options):
    """Normalize selected options and hide the singleton transport option."""
    normalized = [
        {'name': option.get('name'), 'value': option.get('value')}
        for option in (selected_options or [])
        if isinstance(option, dict)
    ]
    if len(normalized) == 1:
        name = (normalized[0].get('name') or '').strip().lower()
        value = (normalized[0].get('value') or '').strip().lower()
        if name == DEFAULT_OPTION_NAME and value == DEFAULT_OPTION_VALUE:
            return []
    return normalized


def singleton_transport_option_values():
    """Required ProductSet transport representation for an Odoo singleton."""
    return [{'optionName': 'Title', 'name': 'Default Title'}]
