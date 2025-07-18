# -*- coding: utf-8 -*-
# from odoo import http


# class CrmMetaLeads2(http.Controller):
#     @http.route('/crm_meta_leads2/crm_meta_leads2', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_meta_leads2/crm_meta_leads2/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_meta_leads2.listing', {
#             'root': '/crm_meta_leads2/crm_meta_leads2',
#             'objects': http.request.env['crm_meta_leads2.crm_meta_leads2'].search([]),
#         })

#     @http.route('/crm_meta_leads2/crm_meta_leads2/objects/<model("crm_meta_leads2.crm_meta_leads2"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_meta_leads2.object', {
#             'object': obj
#         })

