from . import models
# U2: the addon ROOT package is the ONLY place the wizards package is
# registered. `models/__init__.py` must never import this sibling package --
# the wizards import model classes, so a models-level import would create a
# cycle at registry build time.
from . import wizards
