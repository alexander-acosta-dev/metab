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
            api_url = "https://pokeapi.co/api/v2/pokemon/ditto"  # Reemplaza con la URL real de tu API

            # Realizar la solicitud GET a la API
            response = requests.get(api_url)

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