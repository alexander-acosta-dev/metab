# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class ProductAPIController(http.Controller):
    @http.route('/product_api/import', type='json', auth='user')
    def import_products(self):
        ProductAPI = request.env['product.api.import']
        return ProductAPI.import_products_from_api()