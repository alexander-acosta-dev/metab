from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import json

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    
    @api.model
    def importar_productos_desde_api(self):
        """
        Función que importa productos desde la API externa.
        Se ejecuta desde la acción de servidor en el menú de Inventario.
        Muestra un popup con la cantidad de productos creados y actualizados.
        """
        try:
            api_url = "http://seguimiento.random.cl:51034/productos"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...'
            }
            
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise UserError(f"Error al obtener datos de la API: Código {response.status_code}\nRespuesta: {response.text}")
            
            # Validar que la respuesta sea JSON
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' not in content_type:
                raise UserError(f"La API no devolvió JSON válido. Tipo de contenido: {content_type}")
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                raise UserError(f"Respuesta no es JSON válido: {response.text[:200]}...")
            
            # Extraer lista de productos
            productos_data = None
            if isinstance(data, list):
                productos_data = data
            elif isinstance(data, dict):
                posibles_claves = ['productos', 'data', 'items', 'results', 'records']
                for clave in posibles_claves:
                    if clave in data and isinstance(data[clave], list):
                        productos_data = data[clave]
                        break
                if productos_data is None:
                    if 'KOPR' in data and 'NOKOPR' in data:
                        productos_data = [data]
                    else:
                        raise UserError(f"No se encontró lista de productos. Claves disponibles: {list(data.keys())}")
            else:
                raise UserError(f"Formato de respuesta no soportado: {type(data)}")
            
            if not productos_data:
                raise UserError("No se encontraron productos para importar")
            
            # Contadores
            productos_creados = 0
            productos_actualizados = 0
            
            for item in productos_data:
                if not isinstance(item, dict):
                    continue
                kopr = item.get('KOPR')
                nokopr = item.get('NOKOPR')
                poivpr = item.get('POIVPR')
                if not kopr or not nokopr:
                    continue
                
                existing_product = self.env['product.product'].search([('barcode', '=', kopr)], limit=1)
                
                if not existing_product:
                    product_vals = {
                        'name': nokopr,
                        'barcode': kopr,
                        'lst_price': float(poivpr) if poivpr else 0.0,
                        'type': 'consu',
                        'sale_ok': True,
                        'purchase_ok': True,
                    }
                    self.env['product.product'].create(product_vals)
                    productos_creados += 1
                else:
                    update_vals = {
                        'name': nokopr,
                        'lst_price': float(poivpr) if poivpr else existing_product.lst_price,
                    }
                    existing_product.write(update_vals)
                    productos_actualizados += 1
            
            self.env.cr.commit()
            
            # Mostrar resumen al usuario
            raise UserError(
                f"Importación completada:\n• Productos creados: {productos_creados}\n• Productos actualizados: {productos_actualizados}"
            )
            
        except requests.exceptions.Timeout:
            raise UserError("Tiempo de espera agotado al conectar con la API. Inténtalo de nuevo.")
        except requests.exceptions.ConnectionError:
            raise UserError("Error de conexión con la API. Verifica que el servidor esté disponible.")
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error de conexión a la API: {str(e)}")
        except json.JSONDecodeError as e:
            raise UserError(f"Error al decodificar la respuesta JSON: {str(e)}")
        except ValueError as e:
            raise UserError(f"Error en los datos recibidos: {str(e)}")
        except Exception as e:
            self.env.cr.rollback()
            raise UserError(f"Error inesperado al importar productos: {str(e)}")
