{
    'name': 'Adams Dashboard — Native Financial Reports',
    'version': '19.0.1.6.0',
    'summary': 'Company-specific mappings to evaluated Odoo accounting reports',
    'author': 'Adams',
    'license': 'LGPL-3',
    'depends': ['adams_executive_dashboard', 'account_reports'],
    'data': ['security/finance_security.xml', 'security/ir.model.access.csv',
             'views/finance_mapping.xml'],
    'installable': True,
    'application': False,
}
