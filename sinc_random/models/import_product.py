# -*- coding: utf-8 -*-
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
        Importa productos desde API externa con sus precios correspondientes
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
                if productos_response.text:
                    error_msg += f"\nRespuesta: {productos_response.text[:200]}..."
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
                    _logger.info("Datos de precios obtenidos correctamente")
                except ValueError:
                    _logger.warning("Respuesta de precios no es JSON válido")
            else:
                _logger.warning(f"Error al obtener precios: {precios_response.status_code}")
            
            # 4. Procesar precios - Versión mejorada
            precios_por_kopr = {}
            for item in precios_data:
                try:
                    kopr = item.get('kopr')
                    if not kopr:
                        continue
                        
                    # Buscar el primer precio bruto disponible en cualquier unidad
                    for unidad in item.get('unidades', []):
                        prunbruto = unidad.get('prunbruto', [{}])
                        if prunbruto and isinstance(prunbruto, list):
                            precio = prunbruto[0].get('f')
                            if precio is not None:  # Acepta 0 como valor válido
                                precios_por_kopr[kopr] = float(precio)
                                break
                except Exception as e:
                    _logger.warning(f"Error procesando precio para KOPR {kopr}: {str(e)}")
                    continue
            
            _logger.info(f"Se procesaron {len(precios_por_kopr)} precios correctamente")
            
            # 5. Procesar productos con precios
            resultados = self._procesar_productos_con_precios(productos_data, precios_por_kopr)
            
            return self._mostrar_notificacion_exito(
                resultados['creados'],
                resultados['actualizados'],
                resultados['sin_precio']
            )
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error de conexión: {str(e)}")
            raise UserError(f"Error de conexión: {str(e)}")
        except Exception as e:
            _logger.exception("Error inesperado al importar productos")
            raise UserError(f"Error inesperado: {str(e)}")
    
    def _procesar_productos_con_precios(self, productos_data, precios_por_kopr):
        """Procesa productos con manejo detallado de precios"""
        ProductProduct = self.env['product.product']
        creados = 0
        actualizados = 0
        sin_precio = 0
        
        for item in productos_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('KOPR')
            nokopr = item.get('NOKOPR')
            
            if not kopr or not nokopr:
                continue
                
            try:
                # Obtener precio (None si no existe en el diccionario)
                precio_bruto = precios_por_kopr.get(kopr)
                
                # Si no encontramos precio en el endpoint de precios, usar POIVPR como fallback
                if precio_bruto is None:
                    precio_bruto = item.get('POIVPR', 0)
                    sin_precio += 1
                
                producto_existente = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                
                vals = {
                    'name': nokopr,
                    'lst_price': float(precio_bruto),
                    'barcode': kopr,
                    'default_code': kopr,
                }
                
                if not producto_existente:
                    vals.update({
                        'type': 'consu',
                        'sale_ok': True,
                        'purchase_ok': True,
                        'standard_price': 0,
                    })
                    ProductProduct.create(vals)
                    creados += 1
                else:
                    producto_existente.write(vals)
                    actualizados += 1
                    
            except Exception as e:
                _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                continue
        
        return {
            'creados': creados,
            'actualizados': actualizados,
            'sin_precio': sin_precio
        }
    
    def _extraer_datos_productos(self, data):
        """Extrae lista de productos de la respuesta API"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            posibles_claves = ['productos', 'data', 'items', 'results', 'records']
            for clave in posibles_claves:
                if clave in data and isinstance(data[clave], list):
                    return data[clave]
            if 'KOPR' in data and 'NOKOPR' in data:
                return [data]
        return None
    
    def _mostrar_notificacion_exito(self, creados, actualizados, sin_precio):
        """Genera acción para mostrar notificación flotante"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Importación completada',
                'message': (
                    f'Productos nuevos: {creados}\n'
                    f'Productos actualizados: {actualizados}\n'
                    f'Productos sin precio en API: {sin_precio}'
                ),
                'sticky': True,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }

        }
    }
 nuevos: {creados}\n'
                    f'Productos actualizados: {actualizados}\n'
                    f'Precios actualizados desde API'
                ),
                'sticky': True,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }