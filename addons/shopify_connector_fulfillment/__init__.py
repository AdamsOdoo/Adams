from . import models
# U1: the addon ROOT package is the ONLY place the wizards package is
# registered. `models/__init__.py` must never import this sibling package --
# doing so creates a duplicate/circular registration path. Enforced by
# tests/test_ui_import_structure.py.
from . import wizards
