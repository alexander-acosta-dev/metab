from odoo import models, fields, api, _
from math import radians, cos, sin, asin, sqrt
import logging
import requests
import unicodedata
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
import urllib.parse

_logger = logging.getLogger(__name__)

class GeoCheckinTask(models.Model):
    _inherit = 'project.task'

    # Campos Check-in
    checkin_latitude = fields.Float(string="Latitud Check-in", digits=(16, 6), help="Latitud registrada durante el check-in del usuario.")
    checkin_longitude = fields.Float(string="Longitud Check-in", digits=(16, 6), help="Longitud registrada durante el check-in del usuario.")
    checkin_datetime = fields.Datetime(string="Fecha Check-in", help="Fecha y hora en que se realizó el check-in.")
    checkin_distance_km = fields.Float(string="Distancia al Cliente (km)", digits=(8, 2), help="Distancia en kilómetros entre la ubicación del check-in y la ubicación del cliente.")

    # Campos Check-out
    checkout_latitude = fields.Float(string="Latitud Check-out", digits=(16, 6), help="Latitud registrada durante el check-out del usuario.")
    checkout_longitude = fields.Float(string="Longitud Check-out", digits=(16, 6), help="Longitud registrada durante el check-out del usuario.")
    checkout_datetime = fields.Datetime(string="Fecha Check-out", help="Fecha y hora en que se realizó el check-out.")
    checkout_distance_km = fields.Float(string="Distancia Check-out (km)", digits=(8, 2), help="Distancia en kilómetros entre la ubicación del check-out y la ubicación del cliente.")

    # Campos relacionados del cliente
    partner_latitude = fields.Float(related='partner_id.partner_latitude', store=True, readonly=True, string="Latitud Cliente", help="Latitud geográfica del cliente asociada a la tarea.")
    partner_longitude = fields.Float(related='partner_id.partner_longitude', store=True, readonly=True, string="Longitud Cliente", help="Longitud geográfica del cliente asociada a la tarea.")

    # Estado del check-in/out
    checkin_status = fields.Selection([
        ('none', 'Sin Check-in'),
        ('checked_in', 'Check-in Realizado'),
        ('checked_out', 'Check-out Realizado')
    ], string="Estado", default='none', help="Estado actual del check-in/out")

    # Campos de seguridad del check-in
    checkin_ip = fields.Char(string="IP Check-in", help="Dirección IP desde la que se realizó el check-in")
    checkin_security_flags = fields.Text(string="Banderas de Seguridad Check-in", help="Información de seguridad detectada durante el check-in")
    checkin_blocked = fields.Boolean(string="Check-in Bloqueado", default=False, help="Indica si el check-in fue bloqueado por razones de seguridad")
    checkin_block_reason = fields.Text(string="Razón del Bloqueo Check-in", help="Motivo por el cual se bloqueó el check-in")

    def _validate_security(self):
        """Validar la seguridad de la conexión antes del check-in"""
        if not hasattr(request, 'session'):
            _logger.warning("❌ No hay sesión HTTP disponible para validar seguridad")
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

        # Guardar información de seguridad
        security_info = {
            'ip': user_ip,
            'vpn': vpn_detectado,
            'proxy': proxy_detectado,
            'datacenter': datacenter_detectado,
            'timezone_mismatch': timezone_mismatch,
            'validation_time': fields.Datetime.now().isoformat()
        }

        self.write({
            'checkin_ip': user_ip,
            'checkin_security_flags': str(security_info)
        })

        # Si hay problemas de seguridad, bloquear
        if issues:
            block_reason = f"Check-in bloqueado por conexión sospechosa: {', '.join(issues)}"
            
            self.write({
                'checkin_blocked': True,
                'checkin_block_reason': block_reason
            })
            
            _logger.warning(f"🚫 {block_reason} - Usuario: {self.env.user.name}, Tarea: {self.name}, IP: {user_ip}")
            
            raise UserError(_(
                "🚫 Check-in bloqueado por seguridad\n\n"
                "Razones detectadas:\n• %s\n\n"
                "IP: %s\n\n"
                "🔒 Por motivos de seguridad, no se permite el check-in con estas condiciones de red.\n"
                "💡 Si necesitas usar una conexión específica por motivos laborales, contacta con el administrador del sistema."
            ) % ("\n• ".join(issues), user_ip))

        _logger.info(f"✅ Validación de seguridad check-in exitosa - Usuario: {self.env.user.name}, Tarea: {self.name}, IP: {user_ip}")
        return True

    def get_location_button(self):
        """Inicia el proceso de check-in con geolocalización"""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

        if self.checkin_datetime:
            raise UserError(_("Ya se ha realizado el check-in para esta tarea."))

        # 🔒 VALIDACIÓN DE SEGURIDAD ANTES DE PROCEDER
        self._validate_security()

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
        _logger.info("=== INICIANDO CHECK-IN PARA TAREA %s ===", task_id)
        _logger.info("Location data recibida: %s", location_data)
        
        task = self.browse(task_id)
        if not task.exists():
            _logger.error("Tarea %s no encontrada", task_id)
            raise UserError(_("Tarea no encontrada."))

        if task.checkin_datetime:
            _logger.error("Tarea %s ya tiene check-in realizado", task.name)
            raise UserError(_("Ya se ha realizado el check-in para esta tarea."))

        # 🔒 VALIDACIÓN DE SEGURIDAD CRÍTICA ANTES DE PROCESAR
        task._validate_security()

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
            _logger.warning("Precisión baja check-in: %.3f m", accuracy)
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

            distance_km = task._haversine(client_lat, client_lon, latitude, longitude)

            _logger.info(f"Distancia calculada check-in: {distance_km:.3f} km")

            # Validar que esté dentro del rango permitido (100 metros)
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
        checkin_time = fields.Datetime.now()
        task.write({
            'checkin_latitude': latitude,
            'checkin_longitude': longitude,
            'checkin_datetime': checkin_time,
            'checkin_distance_km': distance_km,
            'checkin_status': 'checked_in',
            'checkin_blocked': False,  # Marcar como no bloqueado si llegó hasta aquí
        })

        _logger.info(f"✅ Check-in exitoso para la tarea {task.name} - Usuario: {task.env.user.name}")

        return {
            'distance_km': f"{distance_km:.3f}",
            'message': _("Check-in realizado con éxito a %.3f km del cliente.") % distance_km
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

    def reset_security_block(self):
        """Resetear bloqueo de seguridad (solo administradores)"""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Solo los administradores pueden resetear bloqueos de seguridad."))
        
        self.write({
            'checkin_blocked': False,
            'checkin_block_reason': False
        })
        
        _logger.info(f"🔓 Bloqueo de seguridad check-in reseteado por admin - Tarea: {self.name}, Admin: {self.env.user.name}")

    def view_security_details(self):
        """Ver detalles de seguridad del check-in"""
        self.ensure_one()
        if not self.checkin_security_flags:
            raise UserError(_("No hay información de seguridad registrada para esta tarea."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Detalles de Seguridad Check-in - {self.name}',
            'res_model': 'project.task',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }