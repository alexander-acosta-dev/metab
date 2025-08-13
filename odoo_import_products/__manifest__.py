# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
{
    'name': "Importar Productos desde API Externa",
    'summary': """
        Importa productos desde una API externa al inventario de Odoo""",
    'description': """
        Módulo para importar productos desde una API REST externa
        al módulo de inventario de Odoo.
    """,
    'author': "Tu Nombre",
    'website': "http://www.tuempresa.com",
    'category': 'Inventory',
    'version': '18.0.1.0.0',
    'depends': ['base', 'stock'],
    'data': [
        'views/product_template_views.xml',
        'views/product_import_views.xml',
    ],
    'installable': True,
    'application': True,
}