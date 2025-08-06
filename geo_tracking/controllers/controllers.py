# -*- coding: utf-8 -*-
# from odoo import http


# class GeoTracking(http.Controller):
#     @http.route('/geo_tracking/geo_tracking', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/geo_tracking/geo_tracking/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('geo_tracking.listing', {
#             'root': '/geo_tracking/geo_tracking',
#             'objects': http.request.env['geo_tracking.geo_tracking'].search([]),
#         })

#     @http.route('/geo_tracking/geo_tracking/objects/<model("geo_tracking.geo_tracking"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('geo_tracking.object', {
#             'object': obj
#         })

