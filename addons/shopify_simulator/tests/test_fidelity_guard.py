# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Fidelity guard tests — assert that simulator responses contain every field
the connector's GraphQL queries request.

If this test fails, the simulator is missing a field the connector expects,
which means connector import tests give false confidence.

Field lists are maintained here rather than parsed from query strings,
because reliable GraphQL query parsing is fragile.  When a query changes,
update the corresponding list below AND point to the query file in the comment.

Ref: queries are defined in:
  - shopify_connector_pro/shopify_api/queries/order.py   (FETCH_ORDERS)
  - shopify_connector_pro/shopify_api/queries/product.py (FETCH_PRODUCTS)
  - shopify_connector_pro/shopify_api/queries/customer.py (FETCH_CUSTOMERS)
"""
from .common import SimulatorTestCase


# Top-level fields from FETCH_ORDERS (order.py lines 10-121)
ORDER_NODE_FIELDS = {
    'id', 'name', 'createdAt', 'updatedAt',
    'displayFinancialStatus', 'displayFulfillmentStatus',
    'cancelledAt', 'closed', 'note', 'tags',
    'currencyCode', 'presentmentCurrencyCode',
    'totalPriceSet', 'subtotalPriceSet', 'totalShippingPriceSet',
    'totalTaxSet', 'totalDiscountsSet', 'discountCodes',
    'customer', 'shippingAddress', 'billingAddress',
    'lineItems', 'shippingLines',
}

# Top-level fields from FETCH_PRODUCTS (product.py lines 10-60)
PRODUCT_NODE_FIELDS = {
    'id', 'title', 'descriptionHtml', 'vendor', 'productType',
    'tags', 'status', 'handle', 'createdAt', 'updatedAt',
    'options', 'images', 'variants',
}

# Top-level fields from FETCH_CUSTOMERS (customer.py lines 10-43)
CUSTOMER_NODE_FIELDS = {
    'id', 'firstName', 'lastName', 'email', 'phone',
    'tags', 'state', 'createdAt', 'updatedAt',
    'defaultAddress', 'addresses',
}


class TestOrderFidelity(SimulatorTestCase):
    """Simulator order response must contain all fields FETCH_ORDERS requests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        customer = cls._seed_customer(
            first_name='Guard', last_name='Test', email='guard@test.com',
        )
        cls.order = cls._seed_order(
            name='#FIDELITY',
            customer=customer,
            lines=[{'title': 'Widget', 'quantity': 1, 'unit_price': 10.0}],
            shipping_lines=[{'title': 'Standard', 'price': 5.99}],
            ship_address1='123 Main St',
            ship_city='Springfield',
            ship_country='United States',
            ship_country_code='US',
        )

    def test_order_node_has_all_query_fields(self):
        """Every field in FETCH_ORDERS must appear in the simulator response."""
        node = self.order._to_graphql_node()
        for field in ORDER_NODE_FIELDS:
            self.assertIn(
                field, node,
                f"FETCH_ORDERS requests '{field}' but simulator order node omits it. "
                f"Fix sim_order.py _to_graphql_node().",
            )

    def test_order_line_items_structure(self):
        """lineItems must have edges[] and pageInfo.hasNextPage."""
        node = self.order._to_graphql_node()
        li = node['lineItems']
        self.assertIn('edges', li, "lineItems missing 'edges'")
        self.assertIn('pageInfo', li, "lineItems missing 'pageInfo'")
        self.assertIn('hasNextPage', li['pageInfo'],
                       "lineItems.pageInfo missing 'hasNextPage'")
        self.assertIsInstance(li['edges'], list)

    def test_order_shipping_lines_structure(self):
        """shippingLines must be edges/node wrapped (not a flat list)."""
        node = self.order._to_graphql_node()
        sl = node['shippingLines']
        self.assertIn('edges', sl, "shippingLines missing 'edges' wrapper")
        self.assertIsInstance(sl['edges'], list)
        self.assertGreater(len(sl['edges']), 0, "No shipping lines in test order")
        sl_node = sl['edges'][0]['node']
        self.assertIn('title', sl_node)
        self.assertIn('originalPriceSet', sl_node)
        # FETCH_ORDERS requests taxLines on shippingLines (item 3c)
        self.assertIn('taxLines', sl_node,
                      "shipping line node missing 'taxLines'")
        self.assertIsInstance(sl_node['taxLines'], list)

    def test_order_shipping_line_node_money_set(self):
        """Shipping line originalPriceSet must have shopMoney + presentmentMoney."""
        node = self.order._to_graphql_node()
        price_set = node['shippingLines']['edges'][0]['node']['originalPriceSet']
        self.assertIn('shopMoney', price_set)
        self.assertIn('presentmentMoney', price_set)
        self.assertIn('amount', price_set['shopMoney'])
        self.assertIn('currencyCode', price_set['shopMoney'])

    def test_order_line_item_node_fields(self):
        """Line item nodes must contain all connector-expected fields."""
        node = self.order._to_graphql_node()
        li_node = node['lineItems']['edges'][0]['node']
        for field in ('id', 'title', 'quantity', 'originalUnitPriceSet',
                       'discountAllocations', 'taxLines'):
            self.assertIn(field, li_node,
                          f"lineItem node missing '{field}'")

    def test_order_money_set_structure(self):
        """All MoneyV2Set fields must have shopMoney + presentmentMoney."""
        node = self.order._to_graphql_node()
        money_fields = [
            'totalPriceSet', 'subtotalPriceSet', 'totalShippingPriceSet',
            'totalTaxSet', 'totalDiscountsSet',
        ]
        for field in money_fields:
            self.assertIn('shopMoney', node[field],
                          f"{field} missing 'shopMoney'")
            self.assertIn('presentmentMoney', node[field],
                          f"{field} missing 'presentmentMoney'")


class TestProductFidelity(SimulatorTestCase):
    """Simulator product response must contain all fields FETCH_PRODUCTS requests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls._seed_product_with_variants(
            title='Fidelity Sneaker',
            variant_data=[
                {
                    'title': 'Red / 10',
                    'sku': 'SNKR-R10',
                    'price': '89.99',
                    'weight': 0.8,
                    'weight_unit': 'KILOGRAMS',
                    'option1_name': 'Color',
                    'option1_value': 'Red',
                    'option2_name': 'Size',
                    'option2_value': '10',
                },
                {
                    'title': 'Blue / 10',
                    'sku': 'SNKR-B10',
                    'price': '89.99',
                    'weight': 0.8,
                    'weight_unit': 'KILOGRAMS',
                    'option1_name': 'Color',
                    'option1_value': 'Blue',
                    'option2_name': 'Size',
                    'option2_value': '10',
                },
            ],
        )
        # Add an image
        cls.env['sim.shopify.image'].create({
            'product_id': cls.product.id,
            'alt_text': 'Fidelity test image',
        })

    def test_product_node_has_all_query_fields(self):
        """Every field in FETCH_PRODUCTS must appear in the simulator response."""
        node = self.product._to_graphql_node()
        for field in PRODUCT_NODE_FIELDS:
            self.assertIn(
                field, node,
                f"FETCH_PRODUCTS requests '{field}' but simulator product node omits it. "
                f"Fix sim_product.py _to_graphql_node().",
            )

    def test_product_images_structure(self):
        """images must have edges[].node.{id, url, altText}."""
        node = self.product._to_graphql_node()
        images = node['images']
        self.assertIn('edges', images)
        self.assertGreater(len(images['edges']), 0, "No images in test product")
        img_node = images['edges'][0]['node']
        self.assertIn('id', img_node)
        self.assertIn('url', img_node)
        self.assertIn('altText', img_node)

    def test_product_variant_inventory_item_structure(self):
        """Variant inventoryItem must include measurement.weight.{value, unit}."""
        node = self.product._to_graphql_node()
        v_node = node['variants']['edges'][0]['node']
        inv = v_node['inventoryItem']
        self.assertIn('id', inv)
        self.assertIn('measurement', inv,
                       "inventoryItem missing 'measurement'")
        self.assertIn('weight', inv['measurement'],
                       "measurement missing 'weight'")
        weight = inv['measurement']['weight']
        self.assertIn('value', weight)
        self.assertIn('unit', weight)

    def test_product_options_multi_axis(self):
        """Product with Color+Size variants must have 2 option axes."""
        node = self.product._to_graphql_node()
        options = node['options']
        option_names = {o['name'] for o in options}
        self.assertIn('Color', option_names,
                       "Missing 'Color' option axis")
        self.assertIn('Size', option_names,
                       "Missing 'Size' option axis")

    def test_product_variant_selected_options(self):
        """Each variant must have selectedOptions with name+value pairs."""
        node = self.product._to_graphql_node()
        v_node = node['variants']['edges'][0]['node']
        self.assertIn('selectedOptions', v_node)
        self.assertGreater(len(v_node['selectedOptions']), 0)
        opt = v_node['selectedOptions'][0]
        self.assertIn('name', opt)
        self.assertIn('value', opt)


class TestCustomerFidelity(SimulatorTestCase):
    """Simulator customer response must contain all fields FETCH_CUSTOMERS requests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls._seed_customer(
            first_name='Fidelity', last_name='Test',
            email='fidelity@test.com', phone='+1234567890',
            address1='100 Guard St', city='Testburg',
            country='United States', country_code='US',
            province='California', province_code='CA',
            zip_code='90001',
        )

    def test_customer_node_has_all_query_fields(self):
        """Every field in FETCH_CUSTOMERS must appear in the simulator response."""
        node = self.customer._to_graphql_node()
        for field in CUSTOMER_NODE_FIELDS:
            self.assertIn(
                field, node,
                f"FETCH_CUSTOMERS requests '{field}' but simulator customer node omits it. "
                f"Fix sim_customer.py _to_graphql_node().",
            )

    def test_customer_address_fields(self):
        """defaultAddress must contain all address sub-fields from the query."""
        node = self.customer._to_graphql_node()
        addr = node['defaultAddress']
        self.assertIsNotNone(addr)
        for field in ('address1', 'address2', 'city', 'province',
                       'provinceCode', 'country', 'countryCodeV2', 'zip', 'phone'):
            self.assertIn(field, addr,
                          f"defaultAddress missing '{field}'")
