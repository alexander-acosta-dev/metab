from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductAPI(models.Model):
    _name = 'product.api.import'
    _description = 'Importación de Productos desde API'

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Tipo de Operación',
        required=True
    )

    @api.constrains('picking_type_id')
    def _check_picking_type(self):
        """Validación adicional si es necesaria"""
        for record in self:
            if not record.picking_type_id:
                raise ValidationError(_("Debe seleccionar un tipo de operación"))

    def button_import_products(self):
        """Método principal de importación"""
        self.ensure_one()
        try:
            if not self.picking_type_id:
                raise UserError(_("Debe seleccionar un tipo de operación primero"))
                
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
                
                # Marcar el tipo de operación
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
                
        except requests.exceptions.RequestException as e:
            _logger.error("Error de conexión: %s", str(e))
            raise UserError(_("Error de conexión con la API: %s") % str(e))
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e))
            raise UserError(_("Error inesperado: %s") % str(e))