# -*- coding: utf-8 -*-
# from odoo import http


# class UsuariosPortal(http.Controller):
#     @http.route('/usuarios_portal/usuarios_portal', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/usuarios_portal/usuarios_portal/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('usuarios_portal.listing', {
#             'root': '/usuarios_portal/usuarios_portal',
#             'objects': http.request.env['usuarios_portal.usuarios_portal'].search([]),
#         })

#     @http.route('/usuarios_portal/usuarios_portal/objects/<model("usuarios_portal.usuarios_portal"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('usuarios_portal.object', {
#             'object': obj
#         })

