# -*- coding: utf-8 -*-
# pylint: disable=C0325,W0613

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request
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

    # Campos de seguridad del check-out
    checkout_ip = fields.Char(string="IP Check-out", help="Dirección IP desde la que se realizó el check-out")
    checkout_security_flags = fields.Text(string="Banderas Seguridad Check-out", help="Información de seguridad detectada durante el check-out")
    checkout_blocked = fields.Boolean(string="Check-out Bloqueado", default=False, help="Indica si el check-out fue bloqueado por razones de seguridad")
    checkout_block_reason = fields.Text(string="Razón Bloqueo Check-out", help="Motivo por el cual se bloqueó el check-out")

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

    def _validate_checkout_security(self):
        """Validar la seguridad de la conexión antes del check-out"""
        if not hasattr(request, 'session'):
            _logger.warning("❌ No hay sesión HTTP disponible para validar seguridad en check-out")
            return True  # En contexto no-HTTP, permitir

        # Obtener las banderas de la sesión
        vpn_detectado = request.session.get('vpn_detectado', False)
        proxy_detectado = request.session.get('proxy_detectado', False)
        datacenter_detectado = request.session.get('datacenter_detectado', False)
        timezone_mismatch = request.session.get('timezone_mismatch', False)

        # Obtener IP del usuario
        user_ip = "unknown"
        if hasattr(request, 'httprequest'):
            user_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
            if user_ip and ',' in user_ip:
                user_ip = user_ip.split(',')[0].strip()
            if not user_ip:
                user_ip = request.httprequest.environ.get('HTTP_X_REAL_IP')
            if not user_ip:
                user_ip = request.httprequest.remote_addr

        # Crear lista de issues detectados
        issues = []
        if vpn_detectado:
            issues.append("VPN detectado")
        if proxy_detectado:
            issues.append("Proxy detectado")
        if datacenter_detectado:
            issues.append("Conexión desde datacenter")
        if timezone_mismatch:
            issues.append("Zona horaria no coincide")

        # Guardar información de seguridad del check-out
        security_info = {
            'ip': user_ip,
            'vpn': vpn_detectado,
            'proxy': proxy_detectado,
            'datacenter': datacenter_detectado,
            'timezone_mismatch': timezone_mismatch,
            'validation_time': fields.Datetime.now().isoformat()
        }

        self.write({
            'checkout_ip': user_ip,
            'checkout_security_flags': str(security_info)
        })

        # Si hay problemas de seguridad, bloquear
        if issues:
            block_reason = f"Check-out bloqueado por conexión sospechosa: {', '.join(issues)}"
            
            self.write({
                'checkout_blocked': True,
                'checkout_block_reason': block_reason
            })
            
            _logger.warning(f"🚫 {block_reason} - Usuario: {self.env.user.name}, Tarea: {self.name}, IP: {user_ip}")
            
            raise UserError(_(
                "🚫 Check-out bloqueado por seguridad\n\n"
                "Razones detectadas:\n• %s\n\n"
                "IP: %s\n\n"
                "🔒 Por motivos de seguridad, no se permite el check-out con estas condiciones de red.\n"
                "💡 Si necesitas usar una conexión específica por motivos laborales, contacta con el administrador del sistema."
            ) % ("\n• ".join(issues), user_ip))

        _logger.info(f"✅ Validación de seguridad check-out exitosa - Usuario: {self.env.user.name}, Tarea: {self.name}, IP: {user_ip}")
        return True

    def get_checkout_location_button(self):
        """Inicia el proceso de check-out con geolocalización"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

        if not self.checkin_datetime:
            raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))

        if self.checkout_datetime:
            raise UserError(_("Ya se ha realizado el check-out para esta tarea."))

        # 🔒 VALIDACIÓN DE SEGURIDAD ANTES DE PROCEDER
        self._validate_checkout_security()

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

        # 🔒 VALIDACIÓN DE SEGURIDAD CRÍTICA ANTES DE PROCESAR
        task._validate_checkout_security()

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
            _logger.warning("Precisión baja check-out: %.3f m", accuracy)
            return {
                'error_message': _("La precisión de la ubicación es demasiado baja (%.3f m). Intenta nuevamente.") % accuracy,
            }

        partner = task.partner_id
        if partner and partner.partner_latitude and partner.partner_longitude:
            client_lat = partner.partner_latitude
            client_lon = partner.partner_longitude

            _logger.info("Coordenadas del cliente: (%s, %s)", client_lat, client_lon)

            distance_km = task._haversine(client_lat, client_lon, latitude, longitude)

            _logger.info("Distancia calculada en check-out: %.3f km", distance_km)

            # Validar que esté dentro del rango permitido (100 metros)
            if distance_km > 0.10:
                _logger.warning("Check-out fuera de rango para la tarea %s. Distancia: %.3f km.", task.name, distance_km)
                return {
                    'error_message': _("Estás fuera del rango permitido, a %.3f km del cliente.") % distance_km,
                    'distance_km': f"{distance_km:.3f}",
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
            'checkout_blocked': False,  # Marcar como no bloqueado si llegó hasta aquí
        })

        _logger.info("✅ Check-out exitoso para la tarea %s. Duración de visita: %s", task.name, task.visit_duration_formatted)

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

    # MÉTODOS AUXILIARES PARA ADMINISTRACIÓN

    def reset_checkout_security_block(self):
        """Resetear bloqueo de seguridad del check-out (solo administradores)"""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Solo los administradores pueden resetear bloqueos de seguridad."))
        
        self.write({
            'checkout_blocked': False,
            'checkout_block_reason': False
        })
        
        _logger.info(f"🔓 Bloqueo de seguridad check-out reseteado por admin - Tarea: {self.name}, Admin: {self.env.user.name}")

    def view_checkout_security_details(self):
        """Ver detalles de seguridad del check-out"""
        self.ensure_one()
        if not self.checkout_security_flags:
            raise UserError(_("No hay información de seguridad de check-out registrada para esta tarea."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Detalles de Seguridad Check-out - {self.name}',
            'res_model': 'project.task',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }