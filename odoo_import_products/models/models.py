from odoo import models, fields, api
import requests  # Para realizar solicitudes HTTP
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def verificar_conexion_api(self):
        # Función que se ejecuta al hacer clic en el botón
        try:
            # URL de la API
            api_url = "https://pokeapi.co/api/v2/pokemon/ditto"

            # Realizar la solicitud GET a la API
            response = requests.get(api_url)

            # Verificar si la solicitud fue exitosa (código 200)
            if response.status_code == 200:
                # Mostrar un mensaje de éxito
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Éxito',
                        'message': 'Conexión a la API exitosa.',
                        'type': 'success',
                        'sticky': False,
                    },
                }
            else:
                # Mostrar un mensaje de error si la solicitud no fue exitosa
                raise UserError(f"Error al conectar a la API: Código de estado {response.status_code}")

        except requests.exceptions.RequestException as e:
            # Manejar errores de conexión
            raise UserError(f"Error de conexión a la API: {e}")