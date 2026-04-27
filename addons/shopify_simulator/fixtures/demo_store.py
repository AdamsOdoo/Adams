# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Seed a demo store with realistic Shopify data including edge cases.

Usage from Odoo shell or tests:
    from odoo.addons.shopify_simulator.fixtures.demo_store import seed_demo_store
    seed_demo_store(env, config)
"""


def seed_demo_store(env, config):
    """Populate a simulator config with realistic demo data.

    Returns a dict of created records for reference.
    """
    Product = env['sim.shopify.product']
    Variant = env['sim.shopify.variant']
    Customer = env['sim.shopify.customer']
    Order = env['sim.shopify.order']
    OrderLine = env['sim.shopify.order.line']
    ShippingLine = env['sim.shopify.shipping.line']
    Location = env['sim.shopify.location']
    Inventory = env['sim.shopify.inventory.level']

    cid = config.id
    data = {}

    # ── Locations ─────────────────────────────────────────
    loc_primary = Location.search([
        ('config_id', '=', cid), ('is_primary', '=', True),
    ], limit=1)
    if not loc_primary:
        loc_primary = Location.create({
            'config_id': cid, 'name': 'Main Warehouse',
            'address1': '100 Fulfillment Blvd', 'city': 'Dallas',
            'country_code': 'US', 'is_active': True, 'is_primary': True,
        })
    loc_eu = Location.create({
        'config_id': cid, 'name': 'EU Distribution Center',
        'address1': '5 Rue de Commerce', 'city': 'Paris',
        'country_code': 'FR', 'is_active': True, 'is_primary': False,
    })
    data['locations'] = [loc_primary, loc_eu]

    # ── Products ──────────────────────────────────────────

    # 1. Simple product
    p_simple = Product.create({
        'config_id': cid, 'title': 'Classic Widget',
        'vendor': 'WidgetCo', 'product_type': 'Widget',
        'tags': 'bestseller,widget', 'status': 'ACTIVE',
    })
    p_simple.variant_ids.write({'sku': 'WDG-001', 'price': '24.99', 'barcode': '1234567890123'})

    # 2. Multi-variant product (T-Shirt with sizes + colors)
    p_shirt = Product.create({
        'config_id': cid, 'title': 'Premium T-Shirt',
        'vendor': 'FashionBrand', 'product_type': 'Apparel',
        'tags': 'apparel,tshirt,premium', 'status': 'ACTIVE',
    })
    p_shirt.variant_ids.unlink()
    sizes_colors = [
        ('S', 'Black', '29.99', 'TS-S-BLK'),
        ('M', 'Black', '29.99', 'TS-M-BLK'),
        ('L', 'Black', '31.99', 'TS-L-BLK'),
        ('S', 'White', '29.99', 'TS-S-WHT'),
        ('M', 'White', '29.99', 'TS-M-WHT'),
        ('L', 'White', '31.99', 'TS-L-WHT'),
    ]
    for size, color, price, sku in sizes_colors:
        Variant.create({
            'product_id': p_shirt.id, 'title': f'{size} / {color}',
            'sku': sku, 'price': price,
            'option1_name': 'Size', 'option1_value': size,
            'option2_name': 'Color', 'option2_value': color,
        })

    # 3. Product with Arabic title + missing SKU (edge case)
    p_arabic = Product.create({
        'config_id': cid, 'title': 'قهوة عربية فاخرة',
        'vendor': 'مقهى الشام', 'product_type': 'Coffee',
        'tags': 'arabic,coffee,premium', 'status': 'ACTIVE',
        'description_html': '<p>قهوة عربية أصلية مع هيل وزعفران 🌿</p>',
    })
    p_arabic.variant_ids.write({'price': '18.50', 'sku': ''})  # Missing SKU edge case

    # 4. Draft product (shouldn't be imported by connector)
    p_draft = Product.create({
        'config_id': cid, 'title': 'Unreleased Gadget',
        'vendor': 'Stealth Labs', 'product_type': 'Electronics',
        'status': 'DRAFT',
    })

    # 5. Product with zero-price variant (free gift)
    p_free = Product.create({
        'config_id': cid, 'title': 'Free Sticker Pack',
        'vendor': 'PromoItems', 'product_type': 'Promotional',
        'tags': 'free,gift', 'status': 'ACTIVE',
    })
    p_free.variant_ids.write({'sku': 'STCK-FREE', 'price': '0.00'})

    # 6. Archived product
    p_archived = Product.create({
        'config_id': cid, 'title': 'Discontinued Gizmo',
        'vendor': 'OldCo', 'product_type': 'Gadget',
        'status': 'ARCHIVED', 'tags': 'discontinued',
    })

    data['products'] = [p_simple, p_shirt, p_arabic, p_draft, p_free, p_archived]

    # ── Inventory ─────────────────────────────────────────
    for variant in p_simple.variant_ids:
        Inventory.create({
            'config_id': cid, 'variant_id': variant.id,
            'location_id': loc_primary.id, 'available': 150,
        })
    for variant in p_shirt.variant_ids:
        qty = 50 if variant.option1_value != 'L' else 12
        Inventory.create({
            'config_id': cid, 'variant_id': variant.id,
            'location_id': loc_primary.id, 'available': qty,
        })
        Inventory.create({
            'config_id': cid, 'variant_id': variant.id,
            'location_id': loc_eu.id, 'available': qty // 2,
        })

    # ── Customers ─────────────────────────────────────────
    c_alice = Customer.create({
        'config_id': cid, 'first_name': 'Alice', 'last_name': 'Johnson',
        'email': 'alice.johnson@example.com', 'phone': '+14155551234',
        'tags': 'vip,wholesale',
        'address1': '123 Main Street', 'city': 'San Francisco',
        'province': 'California', 'province_code': 'CA',
        'country': 'United States', 'country_code': 'US', 'zip_code': '94102',
    })
    c_ahmed = Customer.create({
        'config_id': cid, 'first_name': 'أحمد', 'last_name': 'سعد',
        'email': 'ahmed.saad@example.com', 'phone': '+966501234567',
        'tags': 'arabic',
        'address1': 'شارع الملك فهد', 'city': 'الرياض',
        'province': 'منطقة الرياض', 'province_code': 'RI',
        'country': 'Saudi Arabia', 'country_code': 'SA', 'zip_code': '11564',
    })
    c_noemail = Customer.create({
        'config_id': cid, 'first_name': 'Walk', 'last_name': 'In',
        'phone': '+442071234567',  # No email — POS customer edge case
        'country_code': False,
    })
    data['customers'] = [c_alice, c_ahmed, c_noemail]

    # ── Orders ────────────────────────────────────────────
    # Order 1: Normal paid order
    o1 = Order.create({
        'config_id': cid, 'name': '#1001',
        'financial_status': 'PAID', 'fulfillment_status': 'UNFULFILLED',
        'currency_code': 'USD', 'customer_id': c_alice.id,
        'total_price': 89.97, 'subtotal_price': 84.97,
        'total_shipping': 5.00, 'total_tax': 7.50,
        'ship_first_name': 'Alice', 'ship_last_name': 'Johnson',
        'ship_address1': '123 Main Street', 'ship_city': 'San Francisco',
        'ship_province': 'California', 'ship_province_code': 'CA',
        'ship_country': 'United States', 'ship_country_code': 'US',
        'ship_zip': '94102',
    })
    OrderLine.create({
        'order_id': o1.id, 'title': 'Classic Widget',
        'quantity': 2, 'sku': 'WDG-001',
        'variant_gid': p_simple.variant_ids[0].shopify_gid,
        'product_gid': p_simple.shopify_gid,
        'unit_price': 24.99, 'tax_amount': 3.75, 'tax_rate': 0.075,
    })
    OrderLine.create({
        'order_id': o1.id, 'title': 'Premium T-Shirt - M / Black',
        'quantity': 1, 'sku': 'TS-M-BLK',
        'variant_gid': p_shirt.variant_ids[1].shopify_gid,
        'product_gid': p_shirt.shopify_gid,
        'unit_price': 29.99, 'tax_amount': 3.75, 'tax_rate': 0.075,
    })
    ShippingLine.create({
        'order_id': o1.id, 'title': 'Standard Shipping',
        'code': 'standard', 'price': 5.00,
    })

    # Order 2: Pending order with discount
    o2 = Order.create({
        'config_id': cid, 'name': '#1002',
        'financial_status': 'PENDING', 'fulfillment_status': 'UNFULFILLED',
        'currency_code': 'USD', 'customer_id': c_ahmed.id,
        'total_price': 45.00, 'subtotal_price': 50.00,
        'total_discounts': 5.00, 'total_tax': 0.0,
        'discount_codes_json': '[{"code": "WELCOME10", "amount": "5.00", "type": "fixed_amount"}]',
        'tags': 'discount,first-order',
    })
    OrderLine.create({
        'order_id': o2.id, 'title': 'قهوة عربية فاخرة',
        'quantity': 3, 'sku': '',
        'variant_gid': p_arabic.variant_ids[0].shopify_gid,
        'product_gid': p_arabic.shopify_gid,
        'unit_price': 18.50, 'total_discount': 5.00,
    })

    # Order 3: Fulfilled order
    o3 = Order.create({
        'config_id': cid, 'name': '#1003',
        'financial_status': 'PAID', 'fulfillment_status': 'FULFILLED',
        'currency_code': 'USD', 'customer_id': c_alice.id,
        'total_price': 0.00, 'subtotal_price': 0.00,
        'note': 'VIP gift — no charge',
    })
    OrderLine.create({
        'order_id': o3.id, 'title': 'Free Sticker Pack',
        'quantity': 1, 'sku': 'STCK-FREE',
        'variant_gid': p_free.variant_ids[0].shopify_gid,
        'product_gid': p_free.shopify_gid,
        'unit_price': 0.00,
    })

    data['orders'] = [o1, o2, o3]
    return data
