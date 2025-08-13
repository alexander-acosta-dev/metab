# -*- coding: utf-8 -*-
{
    'name': 'Importar Productos desde API',
    'version': '1.0',
    'summary': 'Importa productos desde API externa',
    'description': 'Módulo para consumir API FastAPI e importar productos a Odoo',
    'author': 'Tu Nombre',
    'depends': ['base', 'product'],
    'license':'LGPL-3',
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_api_import/static/src/js/api_import.js',
            'product_api_import/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': True,
}