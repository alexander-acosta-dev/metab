# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductPriceAPI(models.Model):
    _name = 'product.price.api'
    _description = 'Importación de precios desde API'

    name = fields.Char(string="Nombre", readonly=True)

    @api.model
    def importar_precios_desde_api(self):
        """
        Importa precios desde API externa y actualiza list_price de los productos en Odoo.
        """
        try:
            # 1. Configuración de la API
            api_url = "http://seguimiento.random.cl:51034/web32/precios/pidelistaprecio"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IkE5NzgyRkQ5LTYzNzgtRjAxMS04OThGLTk4RjJCMzI2NTZCRSIsInVzZXJuYW1lIjoiYWRtaW5Ac29tZS5jb20iLCJpYXQiOjE3NTUxNjMyNTUsImV4cCI6MTc1NTE2Njg1NX0.rly7yNMFUINVrNWkBDvLgAGB2UFK_mu9qoUaAWV3b0I',
                'Content-Type': 'application/json'
            }

            # 2. Obtener datos de la API
            _logger.info("🔗 Consultando API de precios...")
            response = requests.get(api_url, headers=headers, timeout=60)

            if response.status_code != 200:
                raise UserError(f"Error en API: Código {response.status_code}")

            try:
                precios_data = response.json()
            except ValueError:
                raise UserError("Respuesta no es JSON válido")

            if not precios_data or "datos" not in precios_data:
                raise UserError("La API no devolvió datos de productos en la clave 'datos'")

            productos_api = precios_data["datos"]
            if not isinstance(productos_api, list) or not productos_api:
                raise UserError("La clave 'datos' no contiene productos válidos")

            # 3. Construir diccionario {barcode: pnunbruto}
            productos_precio = {}
            for item in productos_api:
                if not isinstance(item, dict):
                    continue
                barcode = item.get('kopr')
                unidades = item.get('unidades', [])
                precio_bruto = 0.0
                if unidades and isinstance(unidades, list):
                    # Tomamos el primer valor válido de pnunbruto
                    first_unit = unidades[0]
                    prunbruto_list = first_unit.get('prunbruto', [])
                    if prunbruto_list and isinstance(prunbruto_list, list):
                        precio_bruto = prunbruto_list[0].get('f', 0.0)
                if barcode and precio_bruto:
                    productos_precio[barcode] = precio_bruto

            if not productos_precio:
                raise UserError("La API no devolvió productos con códigos y precios válidos")

            # 4. Buscar coincidencias en Odoo
            barcodes_api = list(productos_precio.keys())
            productos_odoo = self.env['product.product'].search([('barcode', 'in', barcodes_api)])
            coincidencias = len(productos_odoo)

            # 5. Actualizar precios
            for producto in productos_odoo:
                nuevo_precio = productos_precio.get(producto.barcode)
                if nuevo_precio:
                    producto.list_price = nuevo_precio
                    _logger.info(f"✅ Producto {producto.barcode} actualizado con list_price={nuevo_precio}")

            # 6. Mostrar notificación en Odoo
            message = (
                f"Productos en API: {len(productos_precio)}\n"
                f"Coincidencias encontradas: {coincidencias}\n"
                f"Precios actualizados: {coincidencias}"
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '🔔 Importación de precios',
                    'message': message,
                    'sticky': True,
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'}
                }
            }

        except requests.exceptions.RequestException as e:
            _logger.error(f"🌐 Error de conexión con la API: {str(e)}")
            raise UserError(f"Error al conectar con la API: {str(e)}")
        except Exception as e:
            _logger.error(f"❌ Error inesperado: {str(e)}")
            raise UserError(f"Error inesperado: {str(e)}")
