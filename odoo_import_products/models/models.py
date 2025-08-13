from odoo import models, fields, api
import requests  # Para realizar solicitudes HTTP
from odoo.exceptions import UserError
import json

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def importar_productos_desde_api(self):
        # Función que se ejecuta al hacer clic en el botón
        try:
            # URL de la API
            api_url = "http://seguimiento.random.cl:51034/productos"  # Reemplaza con la URL real de tu API

            # Configurar los headers con el token Bearer
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IkE5NzgyRkQ5LTYzNzgtRjAxMS04OThGLTk4RjJCMzI2NTZCRSIsInVzZXJuYW1lIjoiYWRtaW5Ac29tZS5jb20iLCJpYXQiOjE3NTUxNjMyNTUsImV4cCI6MTc1NTE2Njg1NX0.rly7yNMFUINVrNWkBDvLgAGB2UFK_mu9qoUaAWV3b0I'
            }

            # Realizar la solicitud GET a la API con los headers
            response = requests.get(api_url, headers=headers)

            # Verificar si la solicitud fue exitosa (código 200)
            if response.status_code == 200:
                # Parsear la respuesta JSON
                data = response.json()

                # Iterar sobre los productos en la respuesta
                for item in data:
                    kopr = item.get('KOPR')
                    nokopr = item.get('NOKOPR')
                    poivpr = item.get('POIVPR')

                    # Verificar si el producto ya existe por código de barras
                    existing_product = self.env['product.product'].search([('barcode', '=', kopr)], limit=1)

                    if not existing_product:
                        # Crear un nuevo producto
                        product_vals = {
                            'name': nokopr,
                            'barcode': kopr,
                            'lst_price': poivpr,  # Precio de venta
                            'type': 'product',  # Asegura que sea un producto almacenable
                        }
                        self.env['product.product'].create(product_vals)
                    else:
                        # Actualizar el producto existente (opcional)
                        existing_product.write({
                            'name': nokopr,
                            'lst_price': poivpr,
                        })

                # Mostrar un mensaje de éxito
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Éxito',
                        'message': 'Productos importados correctamente desde la API.',
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                # Mostrar un mensaje de error si la solicitud no fue exitosa
                raise UserError(f"Error al obtener datos de la API: Código de estado {response.status_code}")

        except requests.exceptions.RequestException as e:
            # Manejar errores de conexión
            raise UserError(f"Error de conexión a la API: {e}")
        except json.JSONDecodeError as e:
            # Manejar errores de decodificación JSON
            raise UserError(f"Error al decodificar la respuesta JSON: {e}")
        except Exception as e:
            # Manejar otros errores
            raise UserError(f"Error al importar productos: {e}")

####