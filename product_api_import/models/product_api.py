from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductAPI(models.Model):
    _name = 'product.api.import'
    _description = 'Importación de Productos desde API'

    def button_import_products(self):
        """Método llamado por el botón en la vista"""
        try:
            # URL de tu API FastAPI
            api_url = "http://192.168.1.100:8000/productos"
            response = requests.get(api_url)
            
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
                
                # Mostrar notificación en la interfaz
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Importación completada',
                        'message': f'Productos creados: {created_count}, Actualizados: {updated_count}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                _logger.error(f"Error al consumir API: {response.status_code}")
                raise UserError(f"Error API: {response.status_code}")
                
        except Exception as e:
            _logger.error(f"Excepción al importar productos: {str(e)}")
            raise UserError(f"Error: {str(e)}")