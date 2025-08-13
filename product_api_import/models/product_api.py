from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductAPI(models.Model):
    _name = 'product.api.import'
    _description = 'Importación de Productos desde API'

    def button_import_products(self):
        """Método llamado por el botón en la vista"""
        self.ensure_one()
        try:
            # URL de tu API FastAPI
            api_url = "http://192.168.1.100:8000/productos"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                products_data = response.json().get('data', [])
                created_count = 0
                updated_count = 0
                
                for product in products_data:
                    # Buscar producto por código de barras (barcode)
                    existing_product = self.env['product.product'].search([
                        ('barcode', '=', product.get('KOPR'))
                    ], limit=1)
                    
                    product_vals = {
                        'barcode': product.get('KOPR'),
                        'name': product.get('NOKOPR'),
                        'list_price': product.get('POIVPR', 0),
                        'type': 'product',
                        'detailed_type': 'product',
                    }
                    
                    if existing_product:
                        existing_product.write(product_vals)
                        updated_count += 1
                    else:
                        self.env['product.product'].create(product_vals)
                        created_count += 1
                
                # Mostrar notificación
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
                error_msg = _("Error al consumir API: %s") % response.status_code
                _logger.error(error_msg)
                raise UserError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = _("Error de conexión: %s") % str(e)
            _logger.error(error_msg)
            raise UserError(error_msg)
        except Exception as e:
            error_msg = _("Error inesperado: %s") % str(e)
            _logger.error(error_msg)
            raise UserError(error_msg)