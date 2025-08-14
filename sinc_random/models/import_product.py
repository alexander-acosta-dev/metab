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
        Importa productos desde API externa asignando correctamente precios bruto y neto
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
                error_msg = f"Error HTTP {productos_response.status_code} al obtener productos"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            try:
                productos_data = productos_response.json()
                _logger.debug("Respuesta productos recibida: %s", productos_data)
            except ValueError as e:
                error_msg = "La respuesta de productos no es JSON válido"
                _logger.error("%s: %s", error_msg, str(e))
                raise UserError(error_msg)
            
            # Convertir a lista si es necesario
            if isinstance(productos_data, dict):
                if 'data' in productos_data and isinstance(productos_data['data'], list):
                    productos_data = productos_data['data']
                elif 'items' in productos_data and isinstance(productos_data['items'], list):
                    productos_data = productos_data['items']
                else:
                    productos_data = [productos_data]
            
            if not isinstance(productos_data, list):
                error_msg = "Formato de productos no reconocido"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            _logger.info("Recibidos %d productos para procesar", len(productos_data))
            
            # 3. Obtener precios
            _logger.info("Obteniendo precios desde API...")
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            precios_response = requests.get(precios_url, headers=headers, timeout=60)
            
            precios_info = {}  # Diccionario para almacenar ambos precios por KOPR
            
            if precios_response.status_code == 200:
                try:
                    precios_data = precios_response.json()
                    _logger.debug("Datos de precios recibidos: %s", precios_data)
                    
                    if isinstance(precios_data, list):
                        for item in precios_data:
                            if not isinstance(item, dict):
                                continue
                                
                            kopr = item.get('kopr')
                            if not kopr or not isinstance(kopr, str):
                                continue
                            
                            # Buscar precios en unidades
                            for unidad in item.get('unidades', []):
                                if not isinstance(unidad, dict):
                                    continue
                                
                                # Precio bruto (sales price)
                                prunbruto = unidad.get('prunbruto', [{}])
                                precio_bruto = prunbruto[0].get('f') if isinstance(prunbruto, list) and prunbruto else None
                                
                                # Precio neto (lst_price)
                                prunneto = unidad.get('prunneto', [{}])
                                precio_neto = prunneto[0].get('f') if isinstance(prunneto, list) and prunneto else None
                                
                                if precio_bruto is not None and precio_neto is not None:
                                    precios_info[kopr] = {
                                        'bruto': float(precio_bruto),
                                        'neto': float(precio_neto)
                                    }
                                    break  # Usamos la primera unidad con ambos precios
                except ValueError as e:
                    _logger.warning("Error al decodificar precios: %s", str(e))
            else:
                _logger.warning("Error al obtener precios: Código %s", precios_response.status_code)
            
            _logger.info("Se obtuvieron precios para %d productos", len(precios_info))
            
            # 4. Procesar productos
            ProductProduct = self.env['product.product']
            contador = 0
            productos_sin_precio = 0
            
            for item in productos_data:
                if not isinstance(item, dict):
                    _logger.warning("Ítem no es un diccionario: %s", item)
                    continue
                    
                kopr = item.get('KOPR')
                nokopr = item.get('NOKOPR')
                
                if not kopr or not nokopr:
                    _logger.warning("Producto sin código o nombre: %s", item)
                    continue
                
                if kopr in precios_info:
                    try:
                        precio_info = precios_info[kopr]
                        
                        producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                        vals = {
                            'name': nokopr,
                            'lst_price': precio_info['neto'],  # Precio neto
                            'sales_price': precio_info['bruto'],  # Precio bruto
                            'barcode': kopr,
                            'default_code': kopr,
                            'type': 'consu',
                            'sale_ok': True,
                            'purchase_ok': True,
                        }
                        
                        if not producto:
                            # Para nuevos productos, establecer costo estándar igual al precio neto
                            vals['standard_price'] = precio_info['neto']
                            ProductProduct.create(vals)
                            _logger.debug("Creado producto %s con precios bruto: %s, neto: %s", 
                                        kopr, precio_info['bruto'], precio_info['neto'])
                        else:
                            producto.write(vals)
                            _logger.debug("Actualizado producto %s con precios bruto: %s, neto: %s", 
                                        kopr, precio_info['bruto'], precio_info['neto'])
                        
                        contador += 1
                    except Exception as e:
                        _logger.error("Error procesando producto %s: %s", kopr, str(e), exc_info=True)
                else:
                    productos_sin_precio += 1
                    _logger.info("Producto %s no tiene precios en la API", kopr)
            
            _logger.info("Procesamiento completado: %d con precios, %d sin precios", 
                        contador, productos_sin_precio)
            
            if contador == 0:
                error_msg = "No se encontraron productos con precios válidos para importar"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
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
            _logger.error("Error de conexión: %s", str(e), exc_info=True)
            raise UserError(f"Error de conexión: {str(e)}")
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e), exc_info=True)
            raise UserError(f"Error inesperado: {str(e)}")