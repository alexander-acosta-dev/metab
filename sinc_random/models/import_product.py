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
        Importa productos desde API externa y muestra notificación flotante con resultados
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
            
            if precios_response.status_code != 200:
                _logger.warning("Error al obtener precios, se usarán precios por defecto")
                precios_data = []
            else:
                precios_data = precios_response.json()
            
            # 4. Procesar precios
            precios_por_kopr = self._procesar_precios(precios_data)
            
            # 5. Importar productos con precios
            resultados = self._procesar_productos(productos_data, precios_por_kopr)
            _logger.info(
                "Importación completada: %d creados, %d actualizados",
                resultados['creados'],
                resultados['actualizados']
            )
            
            return self._mostrar_notificacion_exito(
                resultados['creados'],
                resultados['actualizados']
            )
            
        except requests.exceptions.Timeout:
            _logger.error("Timeout al conectar con la API")
            raise UserError("Tiempo de espera agotado. Inténtalo de nuevo.")
        except requests.exceptions.ConnectionError:
            _logger.error("Error de conexión con la API")
            raise UserError("Error de conexión. Verifica que el servidor esté disponible.")
        except Exception as e:
            _logger.exception("Error inesperado al importar productos")
            self.env.cr.rollback()
            raise UserError(f"Error inesperado: {str(e)}")
    
    def _procesar_precios(self, precios_data):
        """Procesa los datos de precios y retorna diccionario {KOPR: precio}"""
        precios_por_kopr = {}
        
        if not isinstance(precios_data, list):
            _logger.warning("Formato de precios no reconocido")
            return precios_por_kopr
            
        for item in precios_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('kopr')
            if not kopr:
                continue
                
            # Buscar precio en la primera unidad con precio válido
            for unidad in item.get('unidades', []):
                if not isinstance(unidad, dict):
                    continue
                    
                prunbruto = unidad.get('prunbruto', [{}])
                if prunbruto and isinstance(prunbruto, list):
                    precio = prunbruto[0].get('f', 0)
                    if precio:
                        precios_por_kopr[kopr] = precio
                        break
            else:
                precios_por_kopr[kopr] = 0
                
        _logger.info("Precios procesados: %d registros", len(precios_por_kopr))
        return precios_por_kopr
    
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
    
    def _procesar_productos(self, productos_data, precios_por_kopr):
        """Procesa cada producto con sus precios y retorna estadísticas"""
        ProductProduct = self.env['product.product']
        creados = 0
        actualizados = 0
        
        for item in productos_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('KOPR')
            nokopr = item.get('NOKOPR')
            
            if not kopr or not nokopr:
                continue
                
            try:
                # Obtener precio (0 si no existe)
                precio_bruto = precios_por_kopr.get(kopr, 0)
                
                producto_existente = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                
                if not producto_existente:
                    self._crear_producto(kopr, nokopr, precio_bruto)
                    creados += 1
                else:
                    self._actualizar_producto(producto_existente, nokopr, precio_bruto)
                    actualizados += 1
            except Exception as e:
                _logger.warning("Error procesando producto %s: %s", kopr, str(e))
                continue
        
        self.env.cr.commit()
        return {'creados': creados, 'actualizados': actualizados}
    
    def _crear_producto(self, codigo, nombre, precio):
        """Crea un nuevo producto con precio"""
        self.env['product.product'].create({
            'name': nombre,
            'barcode': codigo,
            'lst_price': float(precio),
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': True,
            'default_code': codigo,
            'standard_price': 0,  # Costo inicial en 0
        })
    
    def _actualizar_producto(self, producto, nombre, precio):
        """Actualiza producto existente con precio"""
        producto.write({
            'name': nombre,
            'lst_price': float(precio),
        })
    
    def _mostrar_notificacion_exito(self, creados, actualizados):
        """Genera acción para mostrar notificación flotante"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Importación completada',
                'message': (
                    f'Productos nuevos: {creados}\n'
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