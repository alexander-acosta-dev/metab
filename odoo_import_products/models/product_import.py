import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductImportWizard(models.TransientModel):
    _name = 'product.import.wizard'
    _description = 'Asistente para importar productos desde API'

    def _default_product_ids(self):
        return self.env.context.get('active_ids', [])

    product_ids = fields.Many2many(
        'product.product',
        default=_default_product_ids,
        string='Productos a actualizar'
    )

    def action_import_products(self):
        self.ensure_one()
        api_url = "http://tu-servidor-fastapi/productos"
        
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            products_data = response.json().get('data', [])

            if not products_data:
                raise UserError(_("No se encontraron productos en la API"))

            ProductProduct = self.env['product.product']
            ProductTemplate = self.env['product.template']

            created = updated = 0

            for product_data in products_data:
                barcode = product_data.get('KOPR')
                existing_product = ProductProduct.search([('barcode', '=', barcode)], limit=1)

                vals = {
                    'name': product_data.get('NOKOPR', '').strip(),
                    'barcode': barcode,
                    'list_price': float(product_data.get('POIVPR', 0)),
                    'type': 'product',
                }

                if existing_product:
                    existing_product.write(vals)
                    updated += 1
                else:
                    ProductTemplate.create(vals)
                    created += 1

            message = _("""
                <b>Importación completada:</b><br/>
                • Productos creados: %(created)d<br/>
                • Productos actualizados: %(updated)d
            """) % {'created': created, 'updated': updated}

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': message,
                    'sticky': True,
                    'type': 'success',
                }
            }

        except requests.exceptions.RequestException as e:
            _logger.error("Error de conexión: %s", e)
            raise UserError(_("Error al conectar con la API: %s") % str(e))
        except ValueError as e:
            _logger.error("Error en datos: %s", e)
            raise UserError(_("Error en los datos recibidos: %s") % str(e))
        except Exception as e:
            _logger.error("Error inesperado: %s", e)
            raise UserError(_("Error inesperado: %s") % str(e))