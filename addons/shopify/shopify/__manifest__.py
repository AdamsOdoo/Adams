{
    "name": "Odoo Shopify Connector",
    "version": "1.2.9",
    "category": "eCommerce",
    "summary": """Integrate and manage your Shopify marketplace directly from Odoo using the TeqStars Shopify Odoo Connector and Shopify Odoo Marketplace Integration solution. This Odoo Shopify Integration and Shopify Integration Odoo module helps automate product sync, order management, inventory updates, shipping workflows, and financial reconciliation. Shopify TeqStars integration provides a fast, reliable, and scalable marketplace automation solution for Odoo.
                  Connect Shopify with Odoo — the Odoo Shopify Connector and Shopify Integration for Odoo, with product sync, order import and stock updates, built on TeqStars Base Marketplace, the shared core behind every TeqStars marketplace connector.""",
    "depends": ['base_marketplace'],

    'data': [
        'security/ir.model.access.csv',

        'report/sale_report_views.xml',

        'wizards/operation_view.xml',
        'views/marketplace_listing_item_view.xml',
        'views/marketplace_listing_view.xml',
        'views/collection_view.xml',

        'views/location_view.xml',
        'views/shopify_tags_view.xml',
        'views/shopify_image_view.xml',
        'views/delivery_carrier_view.xml',
        'views/shopify_payment_gateway_view.xml',
        'views/sale_order_view.xml',
        'views/stock_view.xml',
        'views/shopify_product_category.xml',
        'views/product_category_view.xml',
        'views/shopify_product_type_view.xml',
        'views/shopify_sales_channels_view.xml',
        'views/shopify_mapping_views.xml',
        'views/shopify_metaobject_views.xml',
        'views/shopify_market_view.xml',
        'views/shopify_catalog_view.xml',
        'views/shopify_return_reason_view.xml',
        'views/shopify_bulk_query_view.xml',

        'wizards/cancel_order_in_marketplace_view.xml',
        'wizards/account_payment_register_views.xml',
        'wizards/shopify_payment_refund_wiz.xml',
        'wizards/shopify_sales_channels_wizard_view.xml',
        'wizards/shopify_return_export_wiz.xml',
        'wizards/shopify_return_process_wiz.xml',

        'views/payout_view.xml',
        'views/marketplace_instance_view.xml',
        'views/marketplace_listing_image_view.xml',
        'views/log_view.xml',
        'views/shopify_financial_workflow_config.xml',
        'views/order_workflow_view.xml',
        'views/account_move_view.xml',
        'views/shopify_return_view.xml',
        'views/shopify_menuitem.xml',

        'data/fulfillment_status_data.xml',
        'data/shopify_payout_transaction_type.xml',
        'data/ir_sequence_data.xml',
        'data/data.xml',
        'data/collection_condition_data.xml',
        'data/ir_cron_data.xml',
    ],

    'images': ['static/description/shopify_banner.png'],

    'assets': {
        'web.assets_backend': [
            'shopify/static/src/scss/onboarding.scss',
            'shopify/static/src/scss/operation_help.scss',
            'shopify/static/src/scss/collection.scss',
            'shopify/static/src/js/onboarding/**/*',
            'shopify/static/src/js/views/**/*',
            'shopify/static/src/js/metaobject/**/*',
            'shopify/static/description/css/shopify_metafield_resource.css'
        ],
    },

    "cloc_exclude": [
        "shopify/**/*",  # exclude all files in a folder hierarchy recursively
        'static/description/**/*',  # exclude all files in a folder hierarchy recursively
    ],
    "author": "TeqStars",
    "website": "https://teqstars.com/r/bSq",
    'support': 'support@teqstars.com',
    'maintainer': 'TeqStars',

    'demo': [],

    'external_dependencies': {
        'python': [
            'numpy',
            'scipy',
            'imagehash',
            'PyWavelets',
            'beautifulsoup4',
        ],
    },

    'license': 'OPL-1',
    'live_test_url': 'https://teqstars.com/r/1rY',
    'auto_install': False,
    'installable': True,
    'application': True,
    'qweb': [],
    "price": "379.99",
    "currency": "EUR",
}
