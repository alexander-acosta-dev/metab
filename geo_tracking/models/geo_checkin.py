# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, http
from math import radians, cos, sin, asin, sqrt
import logging
import requests
import json
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class GeoCheckinTask(models.Model):
    _inherit = 'project.task'

    # Campos Check-in
    checkin_latitude = fields.Float(string="Latitud Check-in", digits=(16, 6), help="Latitud registrada durante el check-in del usuario.")
    checkin_longitude = fields.Float(string="Longitud Check-in", digits=(16, 6), help="Longitud registrada durante el check-in del usuario.")
    checkin_datetime = fields.Datetime(string="Fecha Check-in", help="Fecha y hora en que se realizó el check-in.")
    checkin_distance_km = fields.Float(string="Distancia al Cliente (km)", digits=(8, 2), help="Distancia en kilómetros entre la ubicación del check-in y la ubicación del cliente.")
    
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

    def _get_ip_info(self, user_ip):
        """Obtiene la información de la IP usando ip-api.com"""
        try:
            api_url = f"http://ip-api.com/json/{user_ip}?fields=status,message,country,countryCode,regionName,city,timezone,isp,org,as,proxy,hosting,mobile,query"
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'fail':
                raise Exception(f"IP-API error: {data.get('message')}")

            # Log all IP data for debugging
            _logger.info(f"IP Info for {user_ip}: {json.dumps(data, indent=2)}")

            return {
                'success': True,
                'proxy': data.get('proxy', False),
                'ip_data': data
            }
        except Exception as e:
            _logger.error(f"❌ IP-API.com falló: {str(e)}")
            return {
                'success': False,
                'proxy': False, # Assume no proxy on failure to avoid blocking valid users
                'error': str(e)
            }

    def get_location_button(self):
        """Inicia el proceso de check-in con geolocalización"""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

        if self.checkin_datetime:
            raise UserError(_("Ya se ha realizado el check-in para esta tarea."))

        provider = self.env['base.geocoder']._get_provider().tech_name
        _logger.info(f"Geolocalización realizada por el proveedor: {provider}")
        self.partner_id.geo_localize()
        
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
        ip_info = {}

        if user_ip:
            ip_info = task._get_ip_info(user_ip)
            task.write({
                'checkin_ip': user_ip,
                'checkin_security_flags': json.dumps(ip_info.get('ip_data'), indent=2)
            })

            if ip_info.get('proxy'):
                block_reason = "Check-in bloqueado por conexión sospechosa: Proxy detectado"
                task.write({
                    'checkin_blocked': True,
                    'checkin_block_reason': block_reason
                })
                _logger.warning(f"🚫 {block_reason} - Usuario: {self.env.user.name}, Tarea: {task.name}, IP: {user_ip}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Proxy Detectado'),
                        'message': _("No se puede realizar el check-in porque se ha detectado el uso de un proxy. Por favor, desactive cualquier proxy o VPN e intente de nuevo."),
                        'type': 'danger',
                        'sticky': True,
                        'ip_data': ip_info.get('ip_data')
                    }
                }
        else:
            _logger.warning("No se pudo obtener la IP del cliente. El check-in continuará sin validación de seguridad.")
            task.write({
                'checkin_ip': 'unknown',
                'checkin_security_flags': "IP del cliente no disponible.",
            })
        
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        accuracy = location_data.get("accuracy")
        distance_km = 0.0

        if not latitude or not longitude:
            _logger.error("No se recibieron datos de ubicación para la tarea %s.", task.name)
            raise UserError(_("No se pudo obtener la ubicación del dispositivo. Asegúrate de que los servicios de ubicación estén activados."))

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
            if distance_km > 0.30:
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
            'message': _("Check-in realizado con éxito a %.3f km del cliente.") % distance_km,
            'ip_data': ip_info.get('ip_data')
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Fórmula de Haversine para calcular distancia entre 2 coordenadas en km."""
        R = 6371.0
        lat1, lon1 = radians(float(lat1)), radians(float(lon1))
        lat2, lon2 = radians(float(lat2)), radians(float(lon2))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))
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
