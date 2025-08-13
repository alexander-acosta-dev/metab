# -*- coding: utf-8 -*-
{
    'name': 'Importación de Productos desde API',
    'version': '1.0',
    'summary': 'Importa productos desde una API externa a Odoo',
    'description': """
        Este módulo permite importar productos desde una API externa y crear registros de productos en Odoo.
    """,
    'category': 'Inventory',
    'author': 'Tu Nombre',
    'license':'LGPL-3',
    'website': 'tu_sitio_web.com',
    'depends': ['stock', 'product'],  # Dependencia del módulo de inventario y producto
    'data': [
        'views/views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}