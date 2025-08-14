from odoo import models, api
import requests
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    
    @api.model
    def importar_productos_desde_api(self):
        """
        Importa productos desde API externa con precios
        """
        try:
            # 1. Configuración de la API
            base_url = "http://seguimiento.random.cl:51034"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...',
                'Content-Type': 'application/json'
            }
            
            # 2. Obtener productos
            _logger.info("Obteniendo productos desde API...")
            productos_url = f"{base_url}/productos"
            productos_response = requests.get(productos_url, headers=headers, timeout=60)
            
            if productos_response.status_code != 200:
                error_msg = f"Error API productos: Código {productos_response.status_code}"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            productos_data = self._extraer_datos_productos(productos_response.json())
            if not productos_data:
                _logger.warning("No se encontraron productos para importar")
                raise UserError("No se encontraron productos para importar")
            
            # 3. Obtener precios
            _logger.info("Obteniendo precios desde API...")
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            precios_response = requests.get(precios_url, headers=headers, timeout=60)
            
            precios_data = []
            if precios_response.status_code == 200:
                try:
                    precios_data = precios_response.json()
                except ValueError:
                    _logger.warning("Respuesta de precios no es JSON válido")
            
            # 4. Procesar precios
            precios_por_kopr = {}
            for item in precios_data:
                kopr = item.get('kopr')
                if kopr:
                    for unidad in item.get('unidades', []):
                        prunbruto = unidad.get('prunbruto', [{}])
                        if prunbruto and prunbruto[0].get('f') is not None:
                            precios_por_kopr[kopr] = prunbruto[0]['f']
                            break
            
            # 5. Procesar productos
            ProductProduct = self.env['product.product']
            for item in productos_data:
                kopr = item.get('KOPR')
                nokopr = item.get('NOKOPR')
                
                if kopr and nokopr:
                    precio = precios_por_kopr.get(kopr, 0)
                    producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                    
                    vals = {
                        'name': nokopr,
                        'lst_price': float(precio),
                        'barcode': kopr,
                        'default_code': kopr,
                    }
                    
                    if not producto:
                        vals.update({
                            'type': 'consu',
                            'sale_ok': True,
                            'purchase_ok': True,
                            'standard_price': 0,
                        })
                        ProductProduct.create(vals)
                    else:
                        producto.write(vals)
            
            # Mensaje de éxito (estructura exacta solicitada)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Éxito',
                    'message': f'{len(productos_data)} productos importados/actualizados correctamente.',
                    'type': 'success',
                    'sticky': False,
                },
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error de conexión: {str(e)}")
            raise UserError(f"Error de conexión: {str(e)}")
        except Exception as e:
            _logger.exception("Error inesperado al importar productos")
            raise UserError(f"Error inesperado: {str(e)}")
    
    def _extraer_datos_productos(self, data):
        """Extrae lista de productos de la respuesta API"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for clave in ['productos', 'data', 'items', 'results', 'records']:
                if clave in data and isinstance(data[clave], list):
                    return data[clave]
            if 'KOPR' in data and 'NOKOPR' in data:
                return [data]
        return None