# -*- coding: utf-8 -*-
{
    'name': 'CRM Meta Leads Import',
    'version': '1.0',
    'summary': 'Importar leads desde Meta Business al presionar CTRL',
    'category': 'CRM',
    'author': 'Alexander',
    'depends': ['crm'],
    'licence': 'LGPL-3',
    'data': [
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_meta_leads/static/src/js/import_leads_shortcut.js',
        ],
    },
    'installable': True,
    'application': False,
}
