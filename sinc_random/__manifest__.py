# -*- coding: utf-8 -*-
{
    'name': 'Importación de Productos desde API',
    'version': '1.0',
    'summary': 'Importa productos desde una API externa a Odoo',
    'description': """
        Este módulo permite importar productos desde una API externa y crear registros de productos en Odoo.
    """,
    'category': 'Inventory',
    'author': 'Sellside SPA',
    'license':'LGPL-3',
    'website': 'https:/www.sellside.cl',
    'depends': ['base', 'stock', 'product'],
    'data': [
        'views/import_product_views.xml',
        'views/import_price_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}