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
        Importa productos desde API externa con precios completos (venta y costo)
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
            
            # 3. Obtener precios (precio de venta y costo)
            precios_venta = {}
            precios_costo = {}
            
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
                                    # Buscar precios en las unidades
                                    for unidad in item.get('unidades', []):
                                        if isinstance(unidad, dict):
                                            # Precio de venta (prunbruto)
                                            prunbruto = unidad.get('prunbruto')
                                            if isinstance(prunbruto, list) and prunbruto:
                                                precio_venta = prunbruto[0].get('f')
                                                if precio_venta is not None:
                                                    try:
                                                        precios_venta[kopr] = float(precio_venta)
                                                    except (ValueError, TypeError):
                                                        continue
                                            
                                            # Precio de costo (debería venir en otro campo, ajustar según API)
                                            # Ejemplo hipotético - ajustar según estructura real de la API
                                            pruncosto = unidad.get('pruncosto', [{}])
                                            if isinstance(pruncosto, list) and pruncosto:
                                                precio_costo = pruncosto[0].get('f')
                                                if precio_costo is not None:
                                                    try:
                                                        precios_costo[kopr] = float(precio_costo)
                                                    except (ValueError, TypeError):
                                                        continue
                except ValueError:
                    _logger.warning("La respuesta de precios no es JSON válido")

            # 4. Procesar productos (solo aquellos con precios completos)
            ProductProduct = self.env['product.product']
            contador = 0
            productos_incompletos = 0
            
            for item in productos_data:
                if not isinstance(item, dict):
                    continue
                    
                kopr = item.get('KOPR')
                nokopr = item.get('NOKOPR')
                
                if not kopr or not nokopr:
                    continue
                
                # Solo procesar si existe precio de venta y costo
                if kopr in precios_venta and kopr in precios_costo:
                    try:
                        precio_venta = precios_venta[kopr]
                        precio_costo = precios_costo[kopr]
                        
                        producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                        vals = {
                            'name': nokopr,
                            'lst_price': precio_venta,  # Precio de venta
                            'standard_price': precio_costo,  # Precio de costo
                            'barcode': kopr,
                            'default_code': kopr,
                            'type': 'consu',
                            'sale_ok': True,
                            'purchase_ok': True,
                        }
                        
                        if not producto:
                            ProductProduct.create(vals)
                        else:
                            producto.write(vals)
                            
                        contador += 1
                        _logger.info(f"Producto {kopr} procesado - Venta: {precio_venta}, Costo: {precio_costo}")
                    except Exception as e:
                        _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                else:
                    productos_incompletos += 1
                    _logger.warning(f"Producto {kopr} sin precios completos - Venta: {kopr in precios_venta}, Costo: {kopr in precios_costo}")

            _logger.info(f"Procesados {contador} productos completos, {productos_incompletos} con precios incompletos")
            
            if contador == 0:
                raise UserError("No se pudo importar ningún producto con precios completos")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Éxito',
                    'message': f'{contador} productos importados/actualizados correctamente con sus precios.',
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