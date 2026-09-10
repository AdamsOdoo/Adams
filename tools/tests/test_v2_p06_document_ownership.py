"""Static ownership fences for the P06 Odoo read-gateway extensions."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"
CORE = ADDONS / "shopify_connector_core"
PRODUCT = ADDONS / "shopify_connector_product"
SALE = ADDONS / "shopify_connector_sale"
FULFILLMENT = ADDONS / "shopify_connector_fulfillment"


def _source(addon: Path, relative: str) -> str:
    return (addon / relative).read_text(encoding="utf-8")


def _assert_order(test: unittest.TestCase, source: str, before: str, after: str) -> None:
    test.assertIn(before, source)
    test.assertIn(after, source)
    test.assertLess(source.index(before), source.index(after))


class TestP06DocumentOwnership(unittest.TestCase):
    def test_read_purposes_are_exact_for_product_and_sale_job_families(self):
        source = _source(CORE, "models/shopify_connector_api_client.py")
        tree = ast.parse(source)
        assignment = next(
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "BUSINESS_READ_PURPOSE_JOB_PREFIXES"
                for target in node.targets
            )
        )
        purposes = ast.literal_eval(assignment.value)
        self.assertEqual(purposes["product_scan"], ("=product_import_scan",))
        self.assertEqual(purposes["product_import"], ("=product_import_sync",))
        self.assertEqual(purposes["customer_import"], ("=customer_import_sync",))
        self.assertEqual(purposes["order_scan"], ("=order_import_scan",))
        self.assertEqual(purposes["order_import"], ("=order_import_sync",))

    def test_domain_reads_use_fixed_purpose_admission_and_forward_claims(self):
        core = _source(CORE, "models/shopify_connector_read_gateway.py")
        product = _source(PRODUCT, "models/shopify_connector_read_gateway.py")
        sale = _source(SALE, "models/shopify_connector_read_gateway.py")
        self.assertIn("execute_business_read", core)
        self.assertIn("purpose=self.purpose", core)
        self.assertIn("claim=self.claim", core)
        self.assertIn('purpose="product_scan"', product)
        self.assertIn('purpose="product_import"', product)
        self.assertIn('purpose="customer_import"', sale)
        self.assertIn('purpose="order_scan"', sale)
        self.assertIn('purpose="order_import"', sale)
        self.assertNotIn("self.client.execute_business(", core)

    def test_core_does_not_import_optional_domain_implementations(self):
        source = _source(CORE, "models/shopify_connector_read_gateway.py")
        for addon in (
            "shopify_connector_product",
            "shopify_connector_sale",
            "shopify_connector_fulfillment",
        ):
            self.assertNotIn("odoo.addons.%s" % addon, source)
        for method in (
            "read_product_page",
            "read_product",
            "read_customer",
            "read_order_scan_page",
            "read_order_header",
        ):
            self.assertNotIn("def %s" % method, source)

    def test_each_domain_registers_only_its_owned_documents_and_methods(self):
        product = _source(PRODUCT, "models/shopify_connector_read_gateway.py")
        sale = _source(SALE, "models/shopify_connector_read_gateway.py")
        fulfillment = _source(FULFILLMENT, "models/shopify_connector_read_gateway.py")

        for source in (product, sale, fulfillment):
            self.assertIn('_inherit = "shopify.connector.read.gateway"', source)
            self.assertIn("def _extend_documents", source)
            self.assertIn("super()._extend_documents", source)

        self.assertIn("PRODUCT_SCAN_QUERY", product)
        self.assertIn("PRODUCT_IMPORT_QUERY", product)
        self.assertIn("def read_product_page", product)
        self.assertIn("def read_product", product)

        self.assertIn("CUSTOMER_IMPORT_QUERY", sale)
        self.assertIn("ORDER_HEADER_QUERY", sale)
        self.assertIn("ORDER_SCAN_QUERY", sale)
        self.assertIn("def read_customer", sale)
        self.assertIn("def read_order_scan_page", sale)

        self.assertIn("LOCATIONS_QUERY", fulfillment)
        self.assertNotIn("def read_product", fulfillment)
        self.assertNotIn("def read_order", fulfillment)

    def test_extension_imports_follow_document_owners(self):
        product_init = _source(PRODUCT, "models/__init__.py")
        _assert_order(
            self,
            product_init,
            "from . import shopify_connector_product_importer",
            "from . import shopify_connector_read_gateway",
        )
        _assert_order(
            self,
            product_init,
            "from . import shopify_connector_product_scan",
            "from . import shopify_connector_read_gateway",
        )

        sale_init = _source(SALE, "models/__init__.py")
        for owner in (
            "shopify_connector_customer_importer",
            "shopify_connector_order_importer",
            "shopify_connector_order_scan",
        ):
            _assert_order(
                self,
                sale_init,
                "from . import %s" % owner,
                "from . import shopify_connector_read_gateway",
            )

        fulfillment_init = _source(FULFILLMENT, "models/__init__.py")
        _assert_order(
            self,
            fulfillment_init,
            "from . import shopify_connector_fulfillment_reader",
            "from . import shopify_connector_read_gateway",
        )


if __name__ == "__main__":
    unittest.main()
