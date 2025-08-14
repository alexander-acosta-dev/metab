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
        Importa productos desde API con manejo completo de precios y unidades
        """
        try:
            # 1. Configuración API
            base_url = "http://seguimiento.random.cl:51034"
            token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IkE5NzgyRkQ5LTYzNzgtRjAxMS04OThGLTk4RjJCMzI2NTZCRSIsInVzZXJuYW1lIjoiYWRtaW5Ac29tZS5jb20iLCJpYXQiOjE3NTUxNjMyNTUsImV4cCI6MTc1NTE2Njg1NX0.rly7yNMFUINVrNWkBDvLgAGB2UFK_mu9qoUaAWV3b0I"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # 2. Obtener productos
            _logger.info("Obteniendo productos...")
            productos = self._obtener_datos_api(f"{base_url}/productos", headers)
            
            # 3. Obtener precios
            _logger.info("Obteniendo precios...")
            precios = self._obtener_datos_api(f"{base_url}/web32/precios/pidelistaprecio?token={token}", headers)
            
            # 4. Procesar datos
            return self._procesar_productos(productos, precios)
            
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e), exc_info=True)
            raise UserError(f"Error inesperado: {str(e)}")

    def _obtener_datos_api(self, url, headers):
        """Obtiene datos de la API con manejo de errores"""
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict):
                return data.get('data', data)
            return data if isinstance(data, list) else []
            
        except requests.exceptions.RequestException as e:
            _logger.error("Error API %s: %s", url, str(e))
            raise UserError(f"Error al conectar con la API: {str(e)}")
        except ValueError as e:
            _logger.error("Respuesta no es JSON válido: %s", str(e))
            raise UserError("La respuesta de la API no es válida")

    def _procesar_productos(self, productos_data, precios_data):
        """Procesa productos y precios con validación estricta"""
        ProductProduct = self.env['product.product']
        contador = 0
        
        # Estructurar precios por código
        precios_por_kopr = {}
        for item in precios_data:
            if not isinstance(item, dict) or item.get('error'):
                continue
                
            kopr = item.get('kopr')
            if not kopr:
                continue
                
            # Procesar unidades para obtener precios
            for unidad in item.get('unidades', []):
                if not isinstance(unidad, dict):
                    continue
                
                # Precio neto (prunneto)
                precio_neto = self._extraer_precio(unidad.get('prunneto'))
                # Precio bruto (prunbruto)
                precio_bruto = self._extraer_precio(unidad.get('prunbruto'))
                
                if precio_neto and precio_bruto:
                    precios_por_kopr[kopr] = {
                        'neto': precio_neto,
                        'bruto': precio_bruto,
                        'unidad': unidad.get('nombre'),
                        'fraccionable': unidad.get('fraccionable', False)
                    }
                    break  # Usar la primera unidad con precios válidos

        _logger.info("Precios obtenidos para %d productos", len(precios_por_kopr))
        
        # Procesar productos
        for item in productos_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('KOPR')
            nokopr = item.get('NOKOPR')
            
            if not kopr or not nokopr:
                continue
                
            if kopr in precios_por_kopr:
                try:
                    precio_info = precios_por_kopr[kopr]
                    producto = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                    
                    vals = {
                        'name': nokopr,
                        'lst_price': precio_info['neto'],
                        'sales_price': precio_info['bruto'],
                        'barcode': kopr,
                        'default_code': kopr,
                        'type': 'product' if precio_info['fraccionable'] else 'consu',
                        'sale_ok': True,
                        'purchase_ok': True,
                        'standard_price': precio_info['neto'],  # Costo = precio neto
                        'uom_id': self._obtener_unidad(precio_info['unidad']),
                        'uom_po_id': self._obtener_unidad(precio_info['unidad'])
                    }
                    
                    if not producto:
                        ProductProduct.create(vals)
                    else:
                        producto.write(vals)
                        
                    contador += 1
                    _logger.debug("Procesado %s: %s", kopr, nokopr)
                    
                except Exception as e:
                    _logger.error("Error procesando %s: %s", kopr, str(e))
        
        # Resultado
        if contador == 0:
            msg = "No se encontraron productos con precios válidos" if productos_data else "No hay productos para importar"
            _logger.error(msg)
            raise UserError(msg)
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': f'{contador} productos procesados correctamente',
                'type': 'success',
                'sticky': False,
            }
        }

    def _extraer_precio(self, rango_precio):
        """Extrae precio del formato de rango"""
        if isinstance(rango_precio, list) and rango_precio:
            return float(rango_precio[0].get('f', 0))
        return None

    def _obtener_unidad(self, nombre_unidad):
        """Obtiene ID de unidad de medida en Odoo"""
        Uom = self.env['uom.uom']
        if nombre_unidad:
            unidad = Uom.search([('name', '=', nombre_unidad)], limit=1)
            return unidad.id if unidad else Uom.search([], limit=1).id
        return Uom.search([], limit=1).id