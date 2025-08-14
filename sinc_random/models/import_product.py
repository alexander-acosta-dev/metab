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
        Importa productos desde API externa con manejo robusto de precios
        """
        try:
            # 1. Configuración de la API
            base_url = "http://seguimiento.random.cl:51034"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...',
                'Content-Type': 'application/json'
            }
            
            # 2. Obtener productos
            _logger.info("Iniciando importación de productos...")
            productos_url = f"{base_url}/productos"
            
            try:
                productos_response = requests.get(productos_url, headers=headers, timeout=60)
                productos_response.raise_for_status()
                productos_data = productos_response.json()
                _logger.debug("Respuesta de productos recibida: %s", productos_data)
            except requests.exceptions.RequestException as e:
                _logger.error("Error al obtener productos: %s", str(e))
                raise UserError(f"Error al conectar con la API de productos: {str(e)}")
            except ValueError as e:
                _logger.error("Respuesta de productos no es JSON válido: %s", str(e))
                raise UserError("La respuesta de productos no es válida")
            
            # Normalizar estructura de productos
            if isinstance(productos_data, dict):
                productos_data = productos_data.get('data', [productos_data])
            if not isinstance(productos_data, list):
                _logger.error("Formato de productos no reconocido")
                raise UserError("Formato de datos de productos no reconocido")
            
            _logger.info("Se recibieron %d productos para procesar", len(productos_data))
            
            # 3. Obtener precios
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            precios_info = {}
            
            try:
                precios_response = requests.get(precios_url, headers=headers, timeout=60)
                if precios_response.status_code == 200:
                    precios_data = precios_response.json()
                    _logger.debug("Datos de precios recibidos: %s", precios_data)
                    
                    if isinstance(precios_data, list):
                        for item in precios_data:
                            if not isinstance(item, dict):
                                continue
                            
                            kopr = item.get('kopr')
                            if not kopr:
                                continue
                            
                            # Buscar precios en todas las unidades
                            for unidad in item.get('unidades', []):
                                if not isinstance(unidad, dict):
                                    continue
                                
                                try:
                                    # Precio bruto (sales price)
                                    bruto = unidad.get('prunbruto', [{}])[0].get('f')
                                    # Precio neto (lst_price)
                                    neto = unidad.get('prunneto', [{}])[0].get('f')
                                    
                                    if bruto is not None and neto is not None:
                                        precios_info[kopr] = {
                                            'bruto': float(bruto),
                                            'neto': float(neto)
                                        }
                                        break  # Usamos la primera unidad con precios válidos
                                except (TypeError, ValueError) as e:
                                    _logger.warning("Error al procesar precios para %s: %s", kopr, str(e))
                                    continue
            except requests.exceptions.RequestException as e:
                _logger.warning("Error al obtener precios: %s", str(e))
            except ValueError as e:
                _logger.warning("Respuesta de precios no es JSON válido: %s", str(e))
            
            _logger.info("Se obtuvieron precios para %d productos", len(precios_info))
            
            # 4. Procesar productos
            ProductProduct = self.env['product.product']
            contador = 0
            productos_sin_precio = 0
            
            for item in productos_data:
                if not isinstance(item, dict):
                    continue
                    
                kopr = item.get('KOPR')
                nokopr = item.get('NOKOPR')
                
                if not kopr or not nokopr:
                    _logger.warning("Producto sin código o nombre válido: %s", item)
                    continue
                
                if kopr in precios_info:
                    try:
                        precio = precios_info[kopr]
                        producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                        
                        vals = {
                            'name': nokopr,
                            'lst_price': precio['neto'],  # Precio neto
                            'sales_price': precio['bruto'],  # Precio bruto
                            'barcode': kopr,
                            'default_code': kopr,
                            'type': 'consu',
                            'sale_ok': True,
                            'purchase_ok': True,
                        }
                        
                        if not producto:
                            vals['standard_price'] = precio['neto']  # Costo = precio neto
                            ProductProduct.create(vals)
                            _logger.info("Creado producto %s: %s", kopr, nokopr)
                        else:
                            producto.write(vals)
                            _logger.info("Actualizado producto %s: %s", kopr, nokopr)
                        
                        contador += 1
                    except Exception as e:
                        _logger.error("Error al procesar producto %s: %s", kopr, str(e), exc_info=True)
                else:
                    productos_sin_precio += 1
                    _logger.info("Producto %s no tiene precios disponibles", kopr)
            
            # Resultados finales
            _logger.info("Proceso completado: %d productos actualizados, %d sin precios", 
                        contador, productos_sin_precio)
            
            if contador == 0:
                if len(productos_data) > 0:
                    msg = "No se encontraron precios válidos para los productos disponibles"
                else:
                    msg = "No se encontraron productos para importar"
                _logger.error(msg)
                raise UserError(msg)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Éxito' if contador > 0 else 'Advertencia',
                    'message': f"{contador} productos procesados correctamente. {productos_sin_precio} sin precios." if contador > 0 else msg,
                    'type': 'success' if contador > 0 else 'warning',
                    'sticky': False,
                },
            }
            
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e), exc_info=True)
            raise UserError(f"Error inesperado: {str(e)}")