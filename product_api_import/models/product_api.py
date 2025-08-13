from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductAPI(models.Model):
    _name = 'product.api.import'
    _description = 'Importación de Productos desde API'

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Tipo de Operación'
    )

    def button_import_products(self):
        """Método principal de importación"""
        self.ensure_one()
        try:
            api_url = "http://192.168.1.100:8000/productos"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                products_data = response.json().get('data', [])
                created_count = 0
                updated_count = 0
                
                for product in products_data:
                    existing_product = self.env['product.product'].search([
                        ('barcode', '=', product.get('KOPR'))
                    ], limit=1)
                    
                    product_vals = {
                        'barcode': product.get('KOPR'),
                        'name': product.get('NOKOPR'),
                        'list_price': product.get('POIVPR', 0),
                        'type': 'product',
                    }
                    
                    if existing_product:
                        existing_product.write(product_vals)
                        updated_count += 1
                    else:
                        self.env['product.product'].create(product_vals)
                        created_count += 1
                
                # Marcar el tipo de operación si se especificó
                if self.picking_type_id:
                    self.picking_type_id.write({'is_api_import': True})
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Importación completada'),
                        'message': _('Productos creados: %s, Actualizados: %s') % (created_count, updated_count),
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
            else:
                raise UserError(_("Error en la API: Código %s") % response.status_code)
                
        except Exception as e:
            _logger.error("Error en importación: %s", str(e))
            raise UserError(_("Error al importar: %s") % str(e))