# -*- coding: utf-8 -*-
{
    'name': 'Importar Productos desde API',
    'version': '1.0.5',
    'depends': ['base', 'product', 'stock'],
    'license': 'LGPL-3',
    'data': [
        'views/views.xml',
        'views/stock_picking_type_views.xml',
        'views/menu_views.xml',  # Nuevo archivo para menús
    ],
    'assets': {
        'web.assets_backend': [
            'product_api_import/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': True,
}