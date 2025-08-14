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
            api_url = "http://seguimiento.random.cl:51034/productos"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...',
                'Content-Type': 'application/json'
            }
            
            # 2. Llamada a la API
            _logger.info("Iniciando importación de productos desde API...")
            response = requests.get(api_url, headers=headers, timeout=60)
            
            # 3. Validar respuesta HTTP
            if response.status_code != 200:
                error_msg = f"Error API: Código {response.status_code}"
                if response.text:
                    error_msg += f"\nRespuesta: {response.text[:200]}..."
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            # 4. Validar formato JSON
            try:
                data = response.json()
            except ValueError as e:
                _logger.error("Respuesta no es JSON válido: %s", response.text[:200])
                raise UserError("La API devolvió una respuesta no válida (no JSON)")
            
            # 5. Procesar datos de productos
            productos_data = self._extraer_datos_productos(data)
            if not productos_data:
                _logger.warning("No se encontraron productos para importar")
                raise UserError("No se encontraron productos para importar")
            
            # 6. Importar productos
            resultados = self._procesar_productos(productos_data)
            _logger.info(
                "Importación completada: %d creados, %d actualizados",
                resultados['creados'],
                resultados['actualizados']
            )
            
            # 7. Mostrar notificación flotante de éxito
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
    
    def _procesar_productos(self, productos_data):
        """Procesa cada producto y retorna estadísticas"""
        ProductProduct = self.env['product.product']
        creados = 0
        actualizados = 0
        
        for item in productos_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('KOPR')
            nokopr = item.get('NOKOPR')
            poivpr = item.get('POIVPR', 0.0)
            
            if not kopr or not nokopr:
                continue
            
            try:
                producto_existente = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                
                if not producto_existente:
                    self._crear_producto(kopr, nokopr, poivpr)
                    creados += 1
                else:
                    self._actualizar_producto(producto_existente, nokopr, poivpr)
                    actualizados += 1
            except Exception as e:
                _logger.warning("Error procesando producto %s: %s", kopr, str(e))
                continue
        
        self.env.cr.commit()
        return {'creados': creados, 'actualizados': actualizados}
    
    def _crear_producto(self, codigo, nombre, precio):
        """Crea un nuevo producto"""
        self.env['product.product'].create({
            'name': nombre,
            'barcode': codigo,
            'list_price': float(precio),
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': True,
            'default_code': codigo,
        })
    
    def _actualizar_producto(self, producto, nombre, precio):
        """Actualiza producto existente"""
        producto.write({
            'name': nombre,
            'list_price': float(precio),
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
                    f'Productos actualizados: {actualizados}'
                ),
                'sticky': True,  # Permanece hasta que el usuario la cierre
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'  # Cierra cualquier diálogo abierto
                },
            }
        }