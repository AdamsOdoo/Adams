{
    'name': 'POS Sales Report',
    'version': '19.0.1.0.1',
    'summary': 'Point of Sale sales by employee, product, session or date, printed as shown on screen',
    'category': 'Sales/Point of Sale',
    'author': 'Adams',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'pos_hr'],
    'data': [
        'report/pos_sales_report.xml',
        'views/report_pos_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'adams_pos_sales_report/static/src/sales_report_list/**/*',
        ],
        'web.report_assets_common': [
            'adams_pos_sales_report/static/src/report/**/*',
        ],
        'web.assets_tests': [
            'adams_pos_sales_report/static/tests/tours/**/*',
        ],
    },
    'installable': True,
}
