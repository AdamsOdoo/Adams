"""Field-level read checks shared by the dashboard adapters."""


def check_readable(records, field_names):
    """Raise AccessError unless the user may read every known field of ``records``' model.

    Odoo 19 deprecates ``check_field_access_rights``; this keeps its semantics on the
    per-field API that ``read()`` itself enforces: unknown/virtual fields are ignored and
    the superuser bypass comes from ``_has_field_access`` (odoo/orm/models.py), so model
    overrides such as hr.employee's are honoured exactly as a later ``read()`` would.
    """
    for name in field_names:
        field = records._fields.get(name)
        if field is not None:
            records._check_field_access(field, 'read')
    return field_names
