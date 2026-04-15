# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import hashlib
import json


def compute_checksum(data):
    """Compute a stable SHA-256 checksum from a dict.

    Sorts keys recursively to ensure deterministic output regardless
    of dict ordering.
    """
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:32]


def product_checksum(product):
    """Compute checksum for an Odoo product.template record."""
    # Include variant SKUs/prices so variant-level changes trigger re-export
    variant_digest = sorted([
        (v.default_code or '', f"{v.lst_price:.4f}", v.barcode or '')
        for v in product.product_variant_ids
    ])
    return compute_checksum({
        'name': product.name,
        'description_sale': product.description_sale or '',
        'list_price': f"{product.list_price:.4f}",
        'default_code': product.default_code or '',
        'barcode': product.barcode or '',
        'weight': f"{product.weight:.4f}" if product.weight else '0',
        'categ_id': product.categ_id.name or '',
        'variants': variant_digest,
    })


def variant_checksum(variant):
    """Compute checksum for an Odoo product.product record."""
    return compute_checksum({
        'default_code': variant.default_code or '',
        'barcode': variant.barcode or '',
        'lst_price': variant.lst_price,
        'weight': variant.weight,
    })


def customer_checksum(partner):
    """Compute checksum for an Odoo res.partner record."""
    return compute_checksum({
        'name': partner.name,
        'email': partner.email or '',
        'phone': partner.phone or '',
        'mobile': partner.mobile or '',
        'street': partner.street or '',
        'street2': partner.street2 or '',
        'city': partner.city or '',
        'zip': partner.zip or '',
        'state': partner.state_id.code or '',
        'country': partner.country_id.code or '',
    })


def shopify_product_checksum(shopify_data):
    """Compute checksum from a Shopify product node."""
    # Include variant digest so price/sku changes trigger re-import
    variant_digest = sorted([
        (
            (v.get('node') or {}).get('sku', ''),
            (v.get('node') or {}).get('price', ''),
            (v.get('node') or {}).get('barcode', '') or '',
        )
        for v in shopify_data.get('variants', {}).get('edges', [])
    ])
    return compute_checksum({
        'title': shopify_data.get('title', ''),
        'descriptionHtml': shopify_data.get('descriptionHtml', ''),
        'vendor': shopify_data.get('vendor', ''),
        'productType': shopify_data.get('productType', ''),
        'tags': shopify_data.get('tags', []),
        'status': shopify_data.get('status', ''),
        'variants': variant_digest,
    })


def shopify_customer_checksum(shopify_data):
    """Compute checksum from a Shopify customer node."""
    return compute_checksum({
        'firstName': shopify_data.get('firstName', ''),
        'lastName': shopify_data.get('lastName', ''),
        'email': shopify_data.get('email', ''),
        'phone': shopify_data.get('phone', ''),
    })
