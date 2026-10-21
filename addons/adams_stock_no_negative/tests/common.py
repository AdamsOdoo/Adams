from unittest import SkipTest

from odoo.modules.registry import Registry
from odoo.tests.common import get_db_name

NOT_ENOUGH = "Not enough stock of"


def skip_unless_installed(module, model, field=None):
    """Skip a test class whose optional app isn't installed, before its common setup needs it."""
    registry = Registry(get_db_name())
    if model not in registry or (field and field not in registry[model]._fields):
        raise SkipTest(f"{module} is not installed")
