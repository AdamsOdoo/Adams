{
    'name': 'Adams Executive Dashboard',
    'version': '19.0.1.2.0',
    'summary': 'Report-first executive workspace',
    'author': 'Adams',
    'license': 'LGPL-3',
    'depends': ['web', 'account'],
    'data': ['security/dashboard_security.xml', 'views/dashboard.xml'],
    'assets': {'web.assets_backend': [
        'adams_executive_dashboard/static/src/dashboard.js',
        'adams_executive_dashboard/static/src/dashboard.xml',
        'adams_executive_dashboard/static/src/dashboard.scss',
    ]},
    'application': True,
    'installable': True,
}
