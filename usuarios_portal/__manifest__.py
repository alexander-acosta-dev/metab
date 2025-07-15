# -*- coding: utf-8 -*-
{
    'name': "Portal Extension for Brokers",
    'summary': "Custom portal access for brokers",
    'description': "Módulo que añade botones de acceso rápido al portal",
    'author': "Sellside",
    'website': "https://www.sellside.cl",
    'category': 'Portal',
    'version': '0.1',
    'depends': ['portal', 'calendar', 'crm', 'website'], 
    'data': [
        'views/portal_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}