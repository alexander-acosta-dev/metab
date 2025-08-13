# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductImport(models.Model):
    _name = 'product.import'
    _description = 'Importación de Productos desde API'

    def import_products_from_api(self):
        # URL de la API que proporcionaste
        api_url = "http://tu-servidor-fastapi/productos"
        
        try:
            # Hacer la petición GET a la API
            response = requests.get(api_url)
            response.raise_for_status()  # Lanza excepción si hay error HTTP
            
            products_data = response.json().get('data', [])
            
            if not products_data:
                raise UserError(_("No se encontraron productos en la API"))
            
            # Contadores para el resumen
            created = 0
            updated = 0
            
            ProductProduct = self.env['product.product']
            ProductTemplate = self.env['product.template']
            
            for product_data in products_data:
                # Buscar producto existente por código de barras (KOPR)
                product = ProductProduct.search([
                    ('barcode', '=', product_data.get('KOPR'))
                ], limit=1)
                
                vals = {
                    'name': product_data.get('NOKOPR', 'Sin nombre'),
                    'barcode': product_data.get('KOPR'),
                    'list_price': product_data.get('POIVPR', 0),
                    'type': 'product',  # Producto almacenable
                    'detailed_type': 'product',
                }
                
                if product:
                    # Actualizar producto existente
                    product.write(vals)
                    updated += 1
                else:
                    # Crear nuevo producto
                    ProductTemplate.create(vals)
                    created += 1
            
            # Mostrar resumen al usuario
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': f"Importación completada: {created} nuevos productos, {updated} actualizados",
                    'type': 'rainbow_man',
                }
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error("Error al conectar con la API: %s", str(e))
            raise UserError(_("Error al conectar con la API: %s") % str(e))
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e))
            raise UserError(_("Error inesperado: %s") % str(e))