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
        Importa productos desde API externa con diagnóstico mejorado
        """
        try:
            # 1. Configuración de la API
            base_url = "http://seguimiento.random.cl:51034"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...',
                'Content-Type': 'application/json'
            }
            
            # 2. Obtener productos con diagnóstico
            _logger.info("Obteniendo productos desde API...")
            productos_url = f"{base_url}/productos"
            productos_response = requests.get(productos_url, headers=headers, timeout=60)
            
            # Validar respuesta
            if productos_response.status_code != 200:
                error_msg = f"Error HTTP {productos_response.status_code} al obtener productos"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            try:
                productos_data = productos_response.json()
                _logger.debug("Respuesta productos: %s", productos_data)
            except ValueError as e:
                error_msg = "La respuesta de productos no es JSON válido"
                _logger.error("%s: %s", error_msg, str(e))
                raise UserError(error_msg)
            
            # Convertir a lista si es necesario
            if isinstance(productos_data, dict):
                if 'data' in productos_data:
                    productos_data = productos_data['data']
                elif 'items' in productos_data:
                    productos_data = productos_data['items']
                else:
                    productos_data = [productos_data]
            
            if not isinstance(productos_data, list):
                error_msg = "Formato de productos no reconocido"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            _logger.info("Recibidos %d productos", len(productos_data))
            
            # 3. Obtener precios con diagnóstico
            _logger.info("Obteniendo precios desde API...")
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            precios_response = requests.get(precios_url, headers=headers, timeout=60)
            
            precios_por_kopr = {}
            if precios_response.status_code == 200:
                try:
                    precios_data = precios_response.json()
                    _logger.debug("Respuesta precios: %s", precios_data)
                    
                    if isinstance(precios_data, list):
                        for item in precios_data:
                            if not isinstance(item, dict):
                                continue
                                
                            kopr = item.get('kopr')
                            if not kopr or not isinstance(kopr, str):
                                continue
                            
                            for unidad in item.get('unidades', []):
                                if isinstance(unidad, dict):
                                    prunbruto = unidad.get('prunbruto')
                                    if isinstance(prunbruto, list) and prunbruto:
                                        precio = prunbruto[0].get('f')
                                        if precio is not None:
                                            try:
                                                precios_por_kopr[kopr] = float(precio)
                                                break
                                            except (ValueError, TypeError):
                                                continue
                except ValueError as e:
                    _logger.warning("Error al decodificar precios: %s", str(e))
            
            _logger.info("Obtenidos %d precios", len(precios_por_kopr))
            
            # 4. Procesar productos con diagnóstico detallado
            ProductProduct = self.env['product.product']
            contador = 0
            errores = 0
            
            for idx, item in enumerate(productos_data, 1):
                if not isinstance(item, dict):
                    _logger.warning("Ítem %d no es un diccionario", idx)
                    errores += 1
                    continue
                    
                try:
                    kopr = item.get('KOPR')
                    nokopr = item.get('NOKOPR')
                    
                    if not kopr:
                        _logger.warning("Ítem %d sin código KOPR", idx)
                        errores += 1
                        continue
                        
                    if not nokopr:
                        _logger.warning("Producto %s sin nombre", kopr)
                        nokopr = f"Producto {kopr}"
                    
                    # Obtener precio
                    precio = precios_por_kopr.get(kopr, 0.0)
                    
                    # Buscar producto existente
                    producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                    
                    # Preparar valores
                    vals = {
                        'name': nokopr,
                        'lst_price': precio,
                        'barcode': kopr,
                        'default_code': kopr,
                    }
                    
                    if not producto:
                        # Crear nuevo producto
                        vals.update({
                            'type': 'product',
                            'sale_ok': True,
                            'purchase_ok': True,
                            'standard_price': 0.0,
                        })
                        ProductProduct.create(vals)
                        _logger.debug("Creado producto %s", kopr)
                    else:
                        # Actualizar producto existente
                        producto.write(vals)
                        _logger.debug("Actualizado producto %s", kopr)
                    
                    contador += 1
                    
                except Exception as e:
                    _logger.error("Error procesando ítem %d (%s): %s", idx, kopr, str(e))
                    errores += 1
                    continue
            
            _logger.info("Procesados %d productos (%d errores)", contador, errores)
            
            # 5. Mostrar resultado
            if contador == 0:
                if errores > 0:
                    raise UserError("No se pudo importar ningún producto (ver logs para detalles)")
                else:
                    raise UserError("No se encontraron productos para importar")
            
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
            _logger.error("Error de conexión: %s", str(e))
            raise UserError(f"Error de conexión: {str(e)}")
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e))
            raise UserError(f"Error inesperado: {str(e)}")