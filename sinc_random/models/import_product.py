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
        Importa productos desde API externa con manejo de tipos de producto
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
                raise UserError(f"Error al obtener productos: Código {productos_response.status_code}")
            
            try:
                productos_data = productos_response.json()
            except ValueError:
                raise UserError("La respuesta de productos no es JSON válido")
            
            # Convertir a lista si es necesario
            if isinstance(productos_data, dict):
                if 'data' in productos_data:
                    productos_data = productos_data['data']
                else:
                    productos_data = [productos_data]
            
            if not isinstance(productos_data, list):
                raise UserError("Formato de productos no reconocido")
            
            # 3. Obtener precios
            _logger.info("Obteniendo precios desde API...")
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            precios_response = requests.get(precios_url, headers=headers, timeout=60)
            
            precios_por_kopr = {}
            if precios_response.status_code == 200:
                try:
                    precios_data = precios_response.json()
                    if isinstance(precios_data, list):
                        for item in precios_data:
                            if isinstance(item, dict):
                                kopr = item.get('kopr')
                                if kopr and isinstance(kopr, str):
                                    for unidad in item.get('unidades', []):
                                        if isinstance(unidad, dict):
                                            prunbruto = unidad.get('prunbruto', [{}])
                                            if isinstance(prunbruto, list) and prunbruto:
                                                precio = prunbruto[0].get('f')
                                                if precio is not None:
                                                    precios_por_kopr[kopr] = float(precio)
                                                    break
                except ValueError:
                    _logger.warning("La respuesta de precios no es JSON válido")

            # 4. Procesar productos
            ProductProduct = self.env['product.product']
            contador = 0
            
            for item in productos_data:
                if not isinstance(item, dict):
                    continue
                    
                try:
                    kopr = item.get('KOPR')
                    nokopr = item.get('NOKOPR')
                    
                    if not kopr or not nokopr:
                        continue
                        
                    # Obtener precio o usar 0 como valor por defecto
                    precio = float(precios_por_kopr.get(kopr, 0))
                    
                    # Buscar o crear producto
                    producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                    vals = {
                        'name': nokopr,
                        'lst_price': precio,
                        'barcode': kopr,
                        'default_code': kopr,
                        'type': 'consu',  # Cambiado de 'product' a 'consu'
                        'sale_ok': True,
                        'purchase_ok': True,
                        'standard_price': 0.0,
                    }
                    
                    if not producto:
                        ProductProduct.create(vals)
                    else:
                        producto.write(vals)
                        
                    contador += 1
                    
                except Exception as e:
                    _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                    continue

            if contador == 0:
                raise UserError("No se pudo importar ningún producto (ver logs para detalles)")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Éxito',
                    'message': f'{contador} productos importados/actualizados correctamente.',
                    'type': 'success',
                    'sticky': False,
                },
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error de conexión: {str(e)}")
            raise UserError(f"Error de conexión: {str(e)}")
        except Exception as e:
            _logger.error(f"Error inesperado: {str(e)}")
            raise UserError(f"Error inesperado: {str(e)}")