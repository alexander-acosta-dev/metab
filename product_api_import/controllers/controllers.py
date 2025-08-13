# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

class ProductAPIController(http.Controller):
    @http.route('/product_api/import', type='json', auth='user')
    def import_products(self):
        try:
            ProductAPI = request.env['product.api.import']
            result = ProductAPI.button_import_products()
            return {'success': True, 'result': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}