from odoo import http
from odoo.http import request
import requests

class IPCheckController(http.Controller):

    @http.route('/check/ipdetective', type='json', auth='user')
    def check_ipdetective(self, **kw):
        ip = request.httprequest.headers.get('X-Forwarded-For', request.httprequest.remote_addr)
        user_tz = kw.get('timezone')  # enviado desde el frontend

        try:
            resp = requests.get(f'https://api.ipdetective.io/check?ip={ip}', timeout=5)
            data = resp.json()

            is_vpn = data.get('vpn', False)
            is_proxy = data.get('proxy', False)
            is_datacenter = data.get('datacenter', False)
            geo_tz = data.get('timezone', None)

            tz_mismatch = user_tz and geo_tz and user_tz != geo_tz

            return {
                'ip': ip,
                'vpn': is_vpn,
                'proxy': is_proxy,
                'datacenter': is_datacenter,
                'geo_timezone': geo_tz,
                'browser_timezone': user_tz,
                'timezone_mismatch': tz_mismatch
            }

        except Exception as e:
            return {'error': str(e), 'ip': ip}