{
    'name': 'Facebook Conversion API',
    'version': '1.0',
    'category': 'Marketing',
    'summary': 'Integra Odoo con Facebook Conversion API',
    'author': 'Sellside SpA',
    'depends': ['base', 'crm'],
    'data': [
        'security/model_access.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/crm_lead_filter.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
