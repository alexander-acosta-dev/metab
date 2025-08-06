# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, http
from math import radians, cos, sin, asin, sqrt
import logging
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class GeoCheckinTask(models.Model):
    _inherit = 'project.task'
    
    # ... (Otros campos existentes) ...

    @api.model
    def get_location(self, task_id, location_data):
        """Procesa los datos de ubicación y realiza la validación de seguridad."""
        _logger.info("=== INICIANDO CHECK-IN PARA TAREA %s ===", task_id)

        task = self.browse(task_id)
        if not task.exists():
            _logger.error("Tarea %s no encontrada", task_id)
            raise UserError(_("Tarea no encontrada."))

        if task.checkin_datetime:
            _logger.error("Tarea %s ya tiene check-in realizado", task.name)
            raise UserError(_("Ya se ha realizado el check-in para esta tarea."))

        # 🔒 CAPTURA DE IP Y VALIDACIÓN DE SEGURIDAD
        user_ip = location_data.get('ip')
        timezone_client = location_data.get('timezone')

        if not user_ip:
            _logger.warning("No se pudo obtener la IP del cliente. El check-in se realizará sin validación de seguridad.")
            # Continuar sin bloquear, pero registrar la advertencia
            task.write({
                'checkin_ip': 'unknown',
                'checkin_security_flags': "IP del cliente no disponible.",
                'checkin_blocked': False,
            })
        else:
            task._validate_security(user_ip, timezone_client)
        
        # ... (Resto del código para procesar la ubicación) ...
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        accuracy = location_data.get("accuracy")
        distance_km = 0.0

        if not latitude or not longitude:
            _logger.error("No se recibieron datos de ubicación para la tarea %s.", task.name)
            raise UserError(_("No se pudo obtener la ubicación del dispositivo. Asegúrate de que los servicios de ubicación estén activados."))

        # ... (Lógica de precisión y distancia existente) ...
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
            distance_km = task._haversine(client_lat, client_lon, latitude, longitude)
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

        checkin_time = fields.Datetime.now()
        task.write({
            'checkin_latitude': latitude,
            'checkin_longitude': longitude,
            'checkin_datetime': checkin_time,
            'checkin_distance_km': distance_km,
            'checkin_status': 'checked_in',
            'checkin_blocked': False,
        })

        _logger.info(f"✅ Check-in exitoso para la tarea {task.name} - Usuario: {task.env.user.name}")

        return {
            'distance_km': f"{distance_km:.3f}",
            'message': _("Check-in realizado con éxito a %.3f km del cliente.") % distance_km
        }
    
    def _validate_security(self, user_ip, timezone_client):
        """Validar la seguridad de la conexión antes del check-in, recibiendo IP y timezone como parámetros."""
        
        try:
            ip_info = self.env['ip_check.controller']._check_ip_and_flags(user_ip, timezone_client)
        except Exception as e:
            _logger.error(f"Error al obtener información de seguridad de la IP: {e}")
            ip_info = {}

        vpn_detectado = ip_info.get('vpn_detectado', False)
        proxy_detectado = ip_info.get('proxy_detectado', False)
        datacenter_detectado = ip_info.get('datacenter_detectado', False)
        timezone_mismatch = ip_info.get('timezone_mismatch', False)

        issues = []
        if vpn_detectado:
            issues.append("VPN detectado")
        if proxy_detectado:
            issues.append("Proxy detectado")
        if datacenter_detectado:
            issues.append("Conexión desde datacenter")
        if timezone_mismatch:
            issues.append("Zona horaria no coincide")

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