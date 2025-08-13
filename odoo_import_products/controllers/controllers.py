# -*- coding: utf-8 -*-
# from odoo import http


# class OdooImportProducts(http.Controller):
#     @http.route('/odoo_import_products/odoo_import_products', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo_import_products/odoo_import_products/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo_import_products.listing', {
#             'root': '/odoo_import_products/odoo_import_products',
#             'objects': http.request.env['odoo_import_products.odoo_import_products'].search([]),
#         })

#     @http.route('/odoo_import_products/odoo_import_products/objects/<model("odoo_import_products.odoo_import_products"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo_import_products.object', {
#             'object': obj
#         })

