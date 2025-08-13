# -*- coding: utf-8 -*-
{
    'name': "Importar Productos desde API",
    'summary': "Importa productos desde API externa",
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'author': "Tu Nombre",
    'website': "http://www.tuempresa.com",
    'depends': ['stock', 'product'],
    'data': [
        'views/product_import_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}