from odoo import models, fields, api, _
from math import radians, cos, sin, asin, sqrt
import logging
import requests
import unicodedata
from odoo.exceptions import UserError, ValidationError
import urllib.parse

_logger = logging.getLogger(__name__)

class GeoCheckinTask(models.Model):
    _inherit = 'project.task'

    checkin_latitude = fields.Float(string="Latitud Check-in", digits=(16, 6), help="Latitud registrada durante el check-in del usuario.")
    checkin_longitude = fields.Float(string="Longitud Check-in", digits=(16, 6), help="Longitud registrada durante el check-in del usuario.")
    checkin_datetime = fields.Datetime(string="Fecha Check-in", help="Fecha y hora en que se realizó el check-in.")
    checkin_distance_km = fields.Float(string="Distancia al Cliente (km)", digits=(8, 2), help="Distancia en kilómetros entre la ubicación del check-in y la ubicación del cliente.")

    partner_latitude = fields.Float(related='partner_id.partner_latitude', store=True, readonly=True, string="Latitud Cliente", help="Latitud geográfica del cliente asociada a la tarea.")
    partner_longitude = fields.Float(related='partner_id.partner_longitude', store=True, readonly=True, string="Longitud Cliente", help="Longitud geográfica del cliente asociada a la tarea.")

    # def action_update_partner_coordinates(self):
    #     """Actualiza las coordenadas del cliente usando Google Geocoding API"""
    #     self.ensure_one()
    #     if not self.partner_id:
    #         raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

    #     partner = self.partner_id
    #     address_parts = [partner.street, partner.street2, partner.city, partner.state_id.name, partner.zip, partner.country_id.name]
    #     full_address = ", ".join(filter(bool, address_parts))

    #     if not full_address:
    #         raise UserError(_("La dirección del cliente está incompleta. Por favor, asegúrate de que el cliente tenga una dirección válida."))

    #     provider = self.env['base.geocoder']._get_provider().tech_name
    #     _logger.info(f"Geolocalización realizada por el proveedor: {provider}")

    #     partner.geo_localize()
    #     latitude = partner.partner_latitude
    #     longitude = partner.partner_longitude

    #     if latitude is not None and longitude is not None:
    #         partner.write({'partner_latitude': latitude, 'partner_longitude': longitude})

    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'message': _("Coordenadas de '%s' actualizadas a (%.6f, %.6f).") % (partner.display_name, latitude, longitude),
    #                 'type': 'success',
    #                 'sticky': False,
    #             }
    #         }
    #     else:
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'message': _("No se pudieron obtener las coordenadas para la dirección de '%s': %s") % (partner.display_name, full_address),
    #                 'type': 'warning',
    #                 'sticky': True,
    #             }
    #         }

    def get_location_button(self):
        """Inicia el proceso de check-in con geolocalización"""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

        provider = self.env['base.geocoder']._get_provider().tech_name
        _logger.info(f"Geolocalización realizada por el proveedor: {provider}")
        self.partner_id.geo_localize()
        
        # Verificar que el cliente tenga coordenadas
        if not (self.partner_id.partner_latitude and self.partner_id.partner_longitude):
            raise UserError(_("El cliente no tiene coordenadas geográficas. Primero actualiza las coordenadas del cliente usando el botón 'Actualizar Coordenadas Cliente'."))
        
        _logger.info("Botón 'Registrar Check-in' presionado para la tarea %s.", self.name)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'get_geolocation_from_browser',
            'params': {
                'task_id': self.id,
            },
        }

    @api.model
    def get_location(self, task_id, location_data):
        """Procesa los datos de ubicación del check-in"""
        task = self.browse(task_id)
        if not task.exists():
            raise UserError(_("Tarea no encontrada."))

        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        accuracy = location_data.get("accuracy")
        distance_km = 0.0

        if not latitude or not longitude:
            _logger.error("No se recibieron datos de ubicación para la tarea %s.", task.name)
            raise UserError(_("No se pudo obtener la ubicación del dispositivo. Asegúrate de que los servicios de ubicación estén activados."))

        _logger.info("Coordenadas de check-in recibidas: (%s, %s) con precisión de %s metros para la tarea %s",
                 latitude, longitude, accuracy, task.name)

        if accuracy and accuracy > 200:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("La precisión de la ubicación es demasiado baja (%.3f m). Intenta nuevamente.") % accuracy,
                    'type': 'danger',
                    'sticky': True
                }
            }

        partner = task.partner_id
        if partner and partner.partner_latitude and partner.partner_longitude:
            client_lat = partner.partner_latitude
            client_lon = partner.partner_longitude

            _logger.info(f"Coordenadas del cliente: ({client_lat}, {client_lon})")

            distance_km = self._haversine(client_lat, client_lon, latitude, longitude)

            _logger.info(f"Distancia calculada: {distance_km:.3f} km")

            # Validar que esté dentro del rango permitido (100 metros)
            warning_message = False
            if distance_km > 0.10:
                _logger.warning(f"Check-in fuera de rango para la tarea {task.name}. Distancia: {distance_km:.3f} km.")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message':_("Estás fuera del rango permitido, a %.3f km del cliente.") % distance_km,
                        'type': 'danger',
                        'sticky': True,
                    }
                }

        else:
            _logger.warning(f"La tarea {task.name} no tiene coordenadas del cliente válidas.")
            distance_km = 0.0

        # Guardar los datos del check-in
        task.write({
            'checkin_latitude': latitude,
            'checkin_longitude': longitude,
            'checkin_datetime': fields.Datetime.now(),
            'checkin_distance_km': distance_km,
        })

        _logger.info(f"Check-in exitoso para la tarea {task.name}")

        return {
            'distance_km': f"{distance_km:.3f}",
            'message': _("Check-in realizado con éxito a %.3f km del cliente.") % distance_km
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        #Fórmula de Haversine para calcular distancia entre 2 coordenadas en km."""
        R = 6371.0  # radio de la Tierra en km

        # Conversión de grados a radianes
        lat1, lon1 = radians(float(lat1)), radians(float(lon1))
        lat2, lon2 = radians(float(lat2)), radians(float(lon2))

        # Diferencia entre las latitudes y longitudes en radianes
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Fórmula de Haversine
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))

        #Retorno de la distancia en Km
        return R * c