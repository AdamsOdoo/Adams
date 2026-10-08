{
    "name": "Base Marketplace",
    "version": "19.0.1.1.3",
    "category": "Extra",
    'summary': 'Qamah Solutions Base Marketplace: the shared framework behind the Qamah Solutions marketplace connectors (instances, listings, queue jobs, logs, order workflows and the marketplace dashboard).',
    "depends": ['delivery', 'sale_management', 'sale_stock'],

    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',

        'report/sale_report_views.xml',

        'wizards/operation_view.xml',
        'wizards/stock_return_views.xml',
        'wizards/marketplace_scope_wizard_views.xml',

        'views/marketplace_listing_item_view.xml',
        'views/marketplace_listing_view.xml',
        'views/product_view.xml',
        'views/marketplace_listing_image_view.xml',
        'views/sale_view.xml',
        'views/pricelist_view.xml',
        'views/account_move_view.xml',
        'views/stock_view.xml',
        'views/log_view.xml',
        'views/res_partner.xml',
        'views/order_workflow_view.xml',

        'data/ir_sequence_data.xml',
        'data/ir_cron.xml',
        'data/dashboard_data.xml',
        'data/data.xml',

        'views/marketplace_queue_job_line_view.xml',
        'views/marketplace_queue_job_view.xml',
        'views/marketplace_instance_view.xml',
        'views/marketplace_menuitems.xml',

    ],

    'images': ['static/description/base_marketplace_odoo.png'],

    'assets': {
        'web._assets_primary_variables': [
            'base_marketplace/static/src/scss/primary_variables.scss',
        ],
        'web.assets_backend': [
            'base_marketplace/static/src/js/**/*',
            ('remove', 'base_marketplace/static/src/js/chart_lib/**/*'),
            'base_marketplace/static/src/xml/**/*',
            'base_marketplace/static/src/css/dashboard.css',
            'base_marketplace/static/src/scss/instance_dashboard.scss',
            'base_marketplace/static/src/scss/kanban_image_view.scss',
            'base_marketplace/static/src/scss/marketplace_scope_wizard.scss',
            'base_marketplace/static/src/scss/marketplace_onboarding.scss',
            'base_marketplace/static/src/scss/marketplace_onboarding_panel.scss',
        ],
    },
    "cloc_exclude": [
        '**/*.css',  # exclude all scss file from the module
        '**/*.xml',  # exclude all XML files from the module
        'static/src/js/chart_lib/**/*',  # exclude all files in a folder hierarchy recursively
        'static/description/**/*',  # exclude all files in a folder hierarchy recursively
    ],
    "author": "Qamah Solutions",
    'maintainer': 'Qamah Solutions',

    "description": """""",

    'demo': [],
    'license': 'OPL-1',
    'auto_install': False,
    'installable': True,
    'application': False,
}
