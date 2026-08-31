"""Static XML/asset contract checks for the isolated P16 administrator UI.

The files are intentionally not manifest-wired until the W2 gate.  These
checks make that boundary explicit while still catching malformed XML,
accidental menus, secret rendering, and unbounded list configuration.
"""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"


class P16AdminUiContractTest(unittest.TestCase):
    def test_isolated_templates_parse_without_menu_or_secret_fields(self):
        source = (CORE / "static" / "src" / "p16" / "shopify_connector_p16.xml").read_text()
        root = ET.fromstring(source)
        names = {node.attrib.get("t-name") for node in root.iter() if node.attrib.get("t-name")}
        self.assertIn("shopify_connector_core.P16Admin", names)
        self.assertIn("shopify_connector_core.P16CredentialPanel", names)
        self.assertNotIn("menuitem", source)
        # The mode token is a protocol value, not a rendered credential value;
        # the template must not expose a serialized field/name attribute.
        self.assertNotIn('name="access_token"', source)
        self.assertNotIn("client_secret", source)

    def test_native_fallback_is_admin_scoped_and_not_wired_by_a_menu(self):
        source = (CORE / "views" / "shopify_connector_p16_admin_views.xml").read_text()
        root = ET.fromstring(source)
        records = {node.attrib["id"]: node for node in root.findall("record")}
        self.assertIn("action_shopify_connector_p16_admin", records)
        self.assertIn("action_shopify_connector_p16_manage_stores_native", records)
        self.assertNotIn("menuitem", source)
        self.assertIn("group_shopify_connector_admin", source)
        self.assertNotIn("access_token", source)
        self.assertNotIn("client_secret", source)

    def test_p16_js_uses_bounded_reads_and_named_server_commands(self):
        source = (CORE / "static" / "src" / "p16" / "shopify_connector_p16_admin.js").read_text()
        self.assertIn("P16_STORE_LIST_LIMIT", source)
        self.assertIn('"get_store_list_v1"', source)
        self.assertIn('"save_store_settings_group_v1"', source)
        self.assertIn('"replace_credential_v1"', source)
        self.assertIn("commandName,\n                [command]", source)
        self.assertIn('trigger: "user"', source)
        self.assertNotIn("this.state.access_token", source)
        self.assertNotIn("this.state.client_secret", source)


if __name__ == "__main__":
    unittest.main()
