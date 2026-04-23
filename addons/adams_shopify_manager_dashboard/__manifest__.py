{
    'name': 'Adams Shopify Manager Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Manager-facing Shopify dashboard: revenue, AOV, deliveries, abandoned carts, refunds, payouts.',
    'description': (
        'Standalone dashboard addon for store managers. Aggregates KPIs, sales trend, '
        'top products and customers, delivery status, abandoned carts, refunds, and '
        'payouts on top of the adams_shopify connector. Read-only: does not modify '
        'any existing adams_shopify model, view, or data file.'
    ),
    'author': 'Adams',
    'website': 'https://github.com/adamsodoo/adams',
    'license': 'OPL-1',
    'depends': [
        'adams_shopify',
        'sale_management',
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/manager_dashboard_action.xml',
        'views/manager_dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'adams_shopify_manager_dashboard/static/src/scss/manager_dashboard.scss',
            'adams_shopify_manager_dashboard/static/src/js/manager_dashboard/**/*.js',
            'adams_shopify_manager_dashboard/static/src/xml/manager_dashboard/**/*.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
