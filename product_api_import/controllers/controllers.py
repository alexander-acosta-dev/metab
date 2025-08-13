# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

class ProductAPIController(http.Controller):
    @http.route('/product_api/import', type='json', auth='user')
    def import_products(self):
        try:
            ProductAPI = request.env['product.api.import'].with_context(
                from_api_import=True
            )
            return ProductAPI.button_import_products()
        except UserError as e:
            return {'success': False, 'error': e.name}
        except ValidationError as e:
            return {'success': False, 'error': e.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}