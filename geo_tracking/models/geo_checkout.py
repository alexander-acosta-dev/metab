# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, http
from odoo.exceptions import UserError
import logging
from math import radians, cos, sin, asin, sqrt

_logger = logging.getLogger(__name__)

class GeoCheckoutTask(models.Model):
    _inherit = 'project.task'
    
    # ... (Otros campos existentes) ...

    @api.model
    def get_checkout_location(self, task_id, location_data):
        """Procesa los datos de ubicación y realiza la validación de seguridad."""
        _logger.info("=== INICIANDO CHECK-OUT PARA TAREA %s ===", task_id)
        
        task = self.browse(task_id)
        if not task.exists():
            _logger.error("Tarea %s no encontrada", task_id)
            raise UserError(_("Tarea no encontrada."))

        if not task.checkin_datetime:
            _logger.error("Tarea %s no tiene check-in previo", task.name)
            raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))

        if task.checkout_datetime:
            _logger.error("Tarea %s ya tiene check-out realizado", task.name)
            raise UserError(_("Ya se ha realizado el check-out para esta tarea."))

        # 🔒 CAPTURA DE IP Y VALIDACIÓN DE SEGURIDAD
        user_ip = location_data.get('ip')
        timezone_client = location_data.get('timezone')

        if not user_ip:
            _logger.warning("No se pudo obtener la IP del cliente. El check-out se realizará sin validación de seguridad.")
            task.write({
                'checkout_ip': 'unknown',
                'checkout_security_flags': "IP del cliente no disponible.",
                'checkout_blocked': False,
            })
        else:
            task._validate_checkout_security(user_ip, timezone_client)
            
        # ... (Resto del código para procesar la ubicación) ...
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        accuracy = location_data.get("accuracy")
        distance_km = 0.0

        if not latitude or not longitude:
            _logger.error("No se recibieron datos de ubicación para el check-out de la tarea %s.", task.name)
            raise UserError(_("No se pudo obtener la ubicación del dispositivo. Asegúrate de que los servicios de ubicación estén activados."))

        # ... (Lógica de precisión y distancia existente) ...
        if accuracy and accuracy > 200:
            _logger.warning("Precisión baja check-out: %.3f m", accuracy)
            return {
                'error_message': _("La precisión de la ubicación es demasiado baja (%.3f m). Intenta nuevamente.") % accuracy,
            }

        partner = task.partner_id
        if partner and partner.partner_latitude and partner.partner_longitude:
            client_lat = partner.partner_latitude
            client_lon = partner.partner_longitude
            distance_km = task._haversine(client_lat, client_lon, latitude, longitude)
            if distance_km > 0.10:
                _logger.warning("Check-out fuera de rango para la tarea %s. Distancia: %.3f km.", task.name, distance_km)
                return {
                    'error_message': _("Estás fuera del rango permitido, a %.3f km del cliente.") % distance_km,
                    'distance_km': f"{distance_km:.3f}",
                }
        else:
            _logger.warning("La tarea %s no tiene coordenadas del cliente válidas.", task.name)
            distance_km = 0.0

        checkout_time = fields.Datetime.now()
        task.write({
            'checkout_latitude': latitude,
            'checkout_longitude': longitude,
            'checkout_datetime': checkout_time,
            'checkout_distance_km': distance_km,
            'checkin_status': 'checked_out',
            'checkout_blocked': False,
        })

        _logger.info("✅ Check-out exitoso para la tarea %s. Duración de visita: %s", task.name, task.visit_duration_formatted)

        return {
            'distance_km': f"{distance_km:.3f}",
            'duration': task.visit_duration_formatted,
        }
    
    def _validate_checkout_security(self, user_ip, timezone_client):
        """Validar la seguridad de la conexión antes del check-out, recibiendo IP y timezone como parámetros."""
        
        try:
            ip_info = self.env['ip_check.controller']._check_ip_and_flags(user_ip, timezone_client)
        except Exception as e:
            _logger.error(f"Error al obtener información de seguridad de la IP en check-out: {e}")
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
            'checkout_ip': user_ip,
            'checkout_security_flags': str(security_info)
        })

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