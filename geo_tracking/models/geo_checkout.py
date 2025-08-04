# -*- coding: utf-8 -*-
# pylint: disable=C0325,W0613

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from math import radians, cos, sin, asin, sqrt

_logger = logging.getLogger(__name__)


class GeoCheckoutTask(models.Model):
    _inherit = 'project.task'

    # Campos calculados para duración de la visita
    visit_duration = fields.Float(
        string="Duración de Visita (horas)",
        digits=(8, 2),
        compute="_compute_visit_duration",
        store=True,
        help="Tiempo transcurrido entre check-in y check-out en horas."
    )
    visit_duration_formatted = fields.Char(
        string="Duración Formateada",
        compute="_compute_visit_duration_formatted",
        help="Duración de la visita en formato HH:MM"
    )

    @api.depends('checkin_datetime', 'checkout_datetime')
    def _compute_visit_duration(self):
        """Calcula la duración de la visita en horas"""
        for record in self:
            if record.checkin_datetime and record.checkout_datetime:
                delta = record.checkout_datetime - record.checkin_datetime
                record.visit_duration = delta.total_seconds() / 3600.0  # Convertir a horas
            else:
                record.visit_duration = 0.0

    @api.depends('visit_duration')
    def _compute_visit_duration_formatted(self):
        """Calcula la duración formateada en HH:MM"""
        for record in self:
            if record.visit_duration > 0:
                hours = int(record.visit_duration)
                minutes = int((record.visit_duration - hours) * 60)
                record.visit_duration_formatted = f"{hours:02d}:{minutes:02d}"
            else:
                record.visit_duration_formatted = "00:00"

    def get_checkout_location_button(self):
        """Inicia el proceso de check-out con geolocalización"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

        if not self.checkin_datetime:
            raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))

        if self.checkout_datetime:
            raise UserError(_("Ya se ha realizado el check-out para esta tarea."))

        provider = self.env['base.geocoder']._get_provider().tech_name
        _logger.info("Geolocalización realizada por el proveedor: %s", provider)
        self.partner_id.geo_localize()

        # Verificar que el cliente tenga coordenadas
        if not (self.partner_id.partner_latitude and self.partner_id.partner_longitude):
            raise UserError(_("El cliente no tiene coordenadas geográficas. Primero actualiza las coordenadas del cliente."))

        _logger.info("Botón 'Registrar Check-out' presionado para la tarea %s.", self.name)

        return {
            'type': 'ir.actions.client',
            'tag': 'get_geolocation_from_browser_checkout',
            'params': {
                'task_id': self.id,
                'action_type': 'checkout',
            },
        }

    @api.model
    def get_checkout_location(self, task_id, location_data):
        """Procesa los datos de ubicación del check-out"""
        _logger.info("=== INICIANDO CHECK-OUT PARA TAREA %s ===", task_id)
        _logger.info("Location data recibida: %s", location_data)

        task = self.browse(task_id)
        if not task.exists():
            _logger.error("Tarea %s no encontrada", task_id)
            raise UserError(_("Tarea no encontrada."))

        _logger.info("Tarea encontrada: %s", task.name)

        if not task.checkin_datetime:
            _logger.error("Tarea %s no tiene check-in previo", task.name)
            raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))

        if task.checkout_datetime:
            _logger.error("Tarea %s ya tiene check-out realizado", task.name)
            raise UserError(_("Ya se ha realizado el check-out para esta tarea."))

        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        accuracy = location_data.get("accuracy")
        distance_km = 0.0

        if not latitude or not longitude:
            _logger.error("No se recibieron datos de ubicación para el check-out de la tarea %s.", task.name)
            raise UserError(_("No se pudo obtener la ubicación del dispositivo. Asegúrate de que los servicios de ubicación estén activados."))

        _logger.info("Coordenadas de check-out recibidas: (%s, %s) con precisión de %s metros para la tarea %s",
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

            _logger.info("Coordenadas del cliente: (%s, %s)", client_lat, client_lon)

            distance_km = self._haversine(client_lat, client_lon, latitude, longitude)

            _logger.info("Distancia calculada en check-out: %.3f km", distance_km)

            # Validar que esté dentro del rango permitido (100 metros)
            if distance_km > 0.10:
                _logger.warning("Check-out fuera de rango para la tarea %s. Distancia: %.3f km.", task.name, distance_km)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Estás fuera del rango permitido, a %.3f km del cliente.") % distance_km,
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        else:
            _logger.warning("La tarea %s no tiene coordenadas del cliente válidas.", task.name)
            distance_km = 0.0

        # Guardar los datos del check-out
        checkout_time = fields.Datetime.now()
        task.write({
            'checkout_latitude': latitude,
            'checkout_longitude': longitude,
            'checkout_datetime': checkout_time,
            'checkout_distance_km': distance_km,
            'checkin_status': 'checked_out',
        })

        _logger.info("Check-out exitoso para la tarea %s. Duración de visita: %s", task.name, task.visit_duration_formatted)

        return {
            'distance_km': f"{distance_km:.3f}",
            'duration': task.visit_duration_formatted,
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Fórmula de Haversine para calcular distancia entre 2 coordenadas en km."""
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

        # Retorno de la distancia en Km
        return R * c