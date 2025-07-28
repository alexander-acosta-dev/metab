# -*- coding: utf-8 -*-
{
    'name': 'Geo Checkin',

    'summary': 'Registro de check-in georreferenciado para vendedores en visitas a clientes',

    'description': """
Este módulo permite a los vendedores registrar un check-in georreferenciado directamente desde su dispositivo móvil o navegador 
al visitar a un cliente. La ubicación capturada se almacena junto a la tarea a realizar, permitiendo verificar que 
la visita se realizó en el lugar correcto. Ideal para equipos de ventas en terreno.
""",

    'author': 'Sellside',
    'website': 'https://www.sellside.cl',

    'category': 'Services/Field Service',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['industry_fsm', 'web_map'],

    'data': [
        'security/ir.model.access.csv',
        'views/geo_checkin_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'web_map/static/src/map_view/map_renderer.js',
            'geo_checkin/static/src/js/geo_checkin.js',
            'geo_checkin/static/src/map_view/map_renderer.js',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}