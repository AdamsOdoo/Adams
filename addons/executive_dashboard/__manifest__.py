{
    'name': 'Executive Dashboard',
    'version': '19.0.1.0.0',
    'summary': 'One screen for finance, sales, CRM, procurement, inventory and people',
    'category': 'Productivity',
    'author': 'Executive Dashboard',
    'license': 'LGPL-3',
    'depends': ['web', 'account'],
    'data': [
        'security/security.xml',
        'views/settings.xml',
        'views/dashboard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'executive_dashboard/static/src/**/*',
        ],
    },
    'application': True,
    'installable': True,
}
