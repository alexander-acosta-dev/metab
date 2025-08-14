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
        Importa productos desde API externa sin precios por defecto
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
            
            # 3. Obtener precios (solo si la respuesta es exitosa)
            precios_por_kopr = {}
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            precios_response = requests.get(precios_url, headers=headers, timeout=60)
            
            if precios_response.status_code == 200:
                try:
                    precios_data = precios_response.json()
                    if isinstance(precios_data, list):
                        for item in precios_data:
                            if isinstance(item, dict):
                                kopr = item.get('kopr')
                                if kopr and isinstance(kopr, str):
                                    # Buscar el primer precio bruto disponible
                                    for unidad in item.get('unidades', []):
                                        if isinstance(unidad, dict):
                                            prunbruto = unidad.get('prunbruto')
                                            if isinstance(prunbruto, list) and prunbruto:
                                                precio = prunbruto[0].get('f')
                                                if precio is not None:
                                                    try:
                                                        precios_por_kopr[kopr] = float(precio)
                                                        break  # Usar el primer precio encontrado
                                                    except (ValueError, TypeError):
                                                        continue
                except ValueError:
                    _logger.warning("La respuesta de precios no es JSON válido")
            else:
                _logger.warning("No se pudieron obtener precios de la API")

            # 4. Procesar productos (solo aquellos con precio)
            ProductProduct = self.env['product.product']
            contador = 0
            productos_sin_precio = 0
            
            for item in productos_data:
                if not isinstance(item, dict):
                    continue
                    
                kopr = item.get('KOPR')
                nokopr = item.get('NOKOPR')
                
                if not kopr or not nokopr:
                    continue
                
                # Solo procesar si existe precio para este producto
                if kopr in precios_por_kopr:
                    try:
                        precio = precios_por_kopr[kopr]
                        
                        producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                        vals = {
                            'name': nokopr,
                            'lst_price': precio,
                            'barcode': kopr,
                            'default_code': kopr,
                            'type': 'consu',
                            'sale_ok': True,
                            'purchase_ok': True,
                        }
                        
                        # Solo actualizar standard_price si estamos creando el producto
                        if not producto:
                            vals['standard_price'] = 190.0  # Costo inicial en 0
                            ProductProduct.create(vals)
                        else:
                            producto.write(vals)
                            
                        contador += 1
                    except Exception as e:
                        _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                else:
                    productos_sin_precio += 1
                    _logger.info(f"Producto {kopr} sin precio en la API")

            _logger.info(f"Procesados {contador} productos con precio, {productos_sin_precio} sin precio")
            
            if contador == 0:
                raise UserError("No se pudo importar ningún producto con precio válido")
            
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