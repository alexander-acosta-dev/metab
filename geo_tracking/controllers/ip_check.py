from odoo import http
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)

class IPCheckController(http.Controller):

    @http.route('/check/ipdetective', type='json', auth='user', methods=['POST'])
    def check_ipdetective(self, **kw):
        # Obtener IP de forma más robusta
        ip = request.httprequest.headers.get('X-Forwarded-For')
        if ip:
            # Tomar solo la primera IP si hay múltiples
            ip = ip.split(',')[0].strip()
        else:
            ip = request.httprequest.remote_addr
            
        user_tz = kw.get('timezone')  # enviado desde el frontend
        
        _logger.info(f"Checking IP: {ip}, User timezone: {user_tz}")

        try:
            # Agregar headers para evitar bloqueos
            headers = {
                'User-Agent': 'Odoo-IPCheck/1.0',
                'Accept': 'application/json'
            }
            
            resp = requests.get(
                f'https://api.ipdetective.io/check?ip={ip}', 
                timeout=5,
                headers=headers
            )
            
            # Verificar que la respuesta sea exitosa
            resp.raise_for_status()
            
            data = resp.json()
            _logger.info(f"IPDetective response: {data}")

            is_vpn = data.get('vpn', False)
            is_proxy = data.get('proxy', False)
            is_datacenter = data.get('datacenter', False)
            geo_tz = data.get('timezone', None)

            # Verificar timezone mismatch de forma más inteligente
            tz_mismatch = False
            if user_tz and geo_tz:
                # Normalizar timezones para comparación
                user_tz_clean = user_tz.replace('_', '/').replace('-', '/')
                geo_tz_clean = geo_tz.replace('_', '/').replace('-', '/')
                tz_mismatch = user_tz_clean != geo_tz_clean

            result = {
                'ip': ip,
                'vpn': is_vpn,
                'proxy': is_proxy,
                'datacenter': is_datacenter,
                'geo_timezone': geo_tz,
                'browser_timezone': user_tz,
                'timezone_mismatch': tz_mismatch,
                'country': data.get('country', 'Unknown')
            }
            
            _logger.info(f"Final result: {result}")
            return result

        except requests.exceptions.RequestException as e:
            _logger.error(f"Request error: {str(e)}")
            return {
                'error': f'Error de conexión: {str(e)}',
                'ip': ip,
                'vpn': False,
                'proxy': False,
                'datacenter': False,
                'timezone_mismatch': False
            }
            
        except Exception as e:
            _logger.error(f"General error: {str(e)}")
            return {
                'error': str(e), 
                'ip': ip,
                'vpn': False,
                'proxy': False,
                'datacenter': False,
                'timezone_mismatch': False
            }