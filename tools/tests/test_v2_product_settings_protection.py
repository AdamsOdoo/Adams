"""Dependency-free source contracts for product settings protection."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_SOURCE_PATH = (
    ROOT
    / 'addons'
    / 'shopify_connector_core'
    / 'models'
    / 'shopify_connector_store_settings_security.py'
)
PRODUCT_SOURCE_PATH = (
    ROOT
    / 'addons'
    / 'shopify_connector_product'
    / 'models'
    / 'shopify_connector_store_settings.py'
)
P15_SETTINGS_PATH = (
    ROOT / 'addons' / 'shopify_connector_core' / 'models'
    / 'shopify_connector_p15_settings.py'
)
P15_SHARED_PATH = (
    ROOT / 'addons' / 'shopify_connector_core' / 'models'
    / 'shopify_connector_p15_shared.py'
)

PRODUCT_SCAN_STATE_FIELDS = (
    'product_last_import_checkpoint_at',
    'product_last_import_success_at',
    'product_scan_window_start_at',
    'product_scan_window_end_at',
    'product_scan_cursor',
    'product_scan_latest_at',
    'product_scan_page_count',
    'product_scan_generation',
)


def _source(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _method(source: str, name: str) -> str:
    tree = ast.parse(source, filename=str(name))
    node = next(
        item for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    return ast.get_source_segment(source, node)


class TestV2ProductSettingsProtection(unittest.TestCase):

    def test_configuration_generation_has_one_central_policy_owner(self):
        settings = _source(P15_SETTINGS_PATH)
        shared = _source(P15_SHARED_PATH)
        write = _method(settings, 'write')
        self.assertIn('P15_CONFIGURATION_POLICY_FIELDS', shared)
        self.assertIn('vals.pop("configuration_generation", None)', write)
        self.assertIn('ORDER BY id FOR UPDATE', write)
        self.assertIn('configuration_generation, 0) + 1', write)
        for progress_field in PRODUCT_SCAN_STATE_FIELDS:
            self.assertNotIn(progress_field, shared)

    def test_core_protection_is_additive_and_composed(self):
        source = _source(CORE_SOURCE_PATH)
        for name in (
            '_additional_protected_settings_fields',
            '_settings_protected_fields',
            '_additional_settings_write_surfaces',
            '_settings_write_surfaces',
        ):
            with self.subTest(method=name):
                self.assertIn('def %s' % name, source)

        protected = _method(source, '_settings_protected_fields')
        self.assertIn('SETTINGS_PROTECTED_FIELDS', protected)
        self.assertIn('_additional_protected_settings_fields()', protected)
        self.assertIn('|', protected)

        surfaces = _method(source, '_settings_write_surfaces')
        self.assertIn('SETTINGS_WRITE_SURFACES', surfaces)
        self.assertIn('_additional_settings_write_surfaces()', surfaces)
        self.assertIn('|', surfaces)

    def test_core_guards_use_composed_surfaces_and_fields(self):
        source = _source(CORE_SOURCE_PATH)
        service_write = _method(source, '_settings_service_write')
        surface_open = _method(source, '_settings_surface_is_open')
        write = _method(source, 'write')

        self.assertIn('_settings_write_surfaces()', service_write)
        self.assertIn('_settings_write_surfaces()', surface_open)
        self.assertIn('_settings_protected_fields()', write)
        self.assertIn('_settings_surface_is_open()', write)

        # The guards must not bypass the inheritance hooks with the fixed
        # module-level sets directly.
        self.assertNotIn('SETTINGS_WRITE_SURFACES', service_write)
        self.assertNotIn('SETTINGS_WRITE_SURFACES', surface_open)
        self.assertNotIn('SETTINGS_PROTECTED_FIELDS', write)

    def test_product_scan_state_is_protected_and_product_surface_is_additive(self):
        source = _source(PRODUCT_SOURCE_PATH)
        protected = _method(
            source, '_additional_protected_settings_fields',
        )
        surfaces = _method(source, '_additional_settings_write_surfaces')

        self.assertIn(
            'super()._additional_protected_settings_fields()', protected,
        )
        self.assertIn(
            'super()._additional_settings_write_surfaces()', surfaces,
        )
        self.assertIn('_product_scan', surfaces)
        for field_name in PRODUCT_SCAN_STATE_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, source)
                self.assertIn(field_name, protected)


if __name__ == '__main__':
    unittest.main()
