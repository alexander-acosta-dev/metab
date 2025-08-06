from odoo import http
from odoo.http import request
import requests
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class IPCheckController(http.Controller):
    
    # Cache simple en memoria (se reinicia con el servidor)
    _ip_cache = {}
    _cache_duration = 3600  # 1 hora en segundos
    
    def _get_cached_result(self, ip):
        """Obtener resultado desde cache si existe y es válido"""
        if ip in self._ip_cache:
            cached_data, timestamp = self._ip_cache[ip]
            if datetime.now().timestamp() - timestamp < self._cache_duration:
                _logger.info(f"📋 Usando cache para IP: {ip}")
                return cached_data
        return None
    
    def _cache_result(self, ip, data):
        """Guardar resultado en cache"""
        self._ip_cache[ip] = (data, datetime.now().timestamp())
        if len(self._ip_cache) > 100:
            oldest_ip = min(self._ip_cache.keys(), 
                            key=lambda k: self._ip_cache[k][1])
            del self._ip_cache[oldest_ip]
    
    def _check_with_ipapi_com(self, user_ip):
        """API 1: IP-API.com - 1000/mes gratis"""
        try:
            api_url = f"http://ip-api.com/json/{user_ip}?fields=status,message,country,countryCode,region,regionName,city,timezone,isp,org,as,proxy,hosting,mobile,query"
            
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'fail':
                raise Exception(f"IP-API error: {data.get('message')}")
            
            isp_org = f"{data.get('isp', '')} {data.get('org', '')}".lower()
            vpn_indicators = ['vpn', 'proxy', 'tunnel', 'hide', 'anony', 'private', 'secure', 'tor', 'nord', 'express', 'surf']
            is_vpn = any(indicator in isp_org for indicator in vpn_indicators)
            
            return {
                'provider': 'ip-api.com',
                'ip': data.get('query'),
                'country': data.get('country'),
                'region': data.get('regionName'),
                'city': data.get('city'),
                'timezone': data.get('timezone'),
                'isp': data.get('isp'),
                'org': data.get('org'),
                'proxy': data.get('proxy', False),
                'datacenter': data.get('hosting', False),
                'vpn': is_vpn,
                'mobile': data.get('mobile', False),
                'success': True
            }
        except Exception as e:
            _logger.error(f"❌ IP-API.com falló: {str(e)}")
            raise
    
    def _check_with_ipapi_co(self, user_ip):
        """API 2: IPapi.co - 1000/mes gratis"""
        try:
            api_url = f"https://ipapi.co/{user_ip}/json/"
            
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            
            data = response.json()
            if data.get('error'):
                raise Exception(f"IPapi.co error: {data.get('reason')}")
            
            org_text = data.get('org', '').lower()
            asn_text = data.get('asn', '').lower()
            
            vpn_indicators = ['vpn', 'proxy', 'tunnel', 'hide', 'anony', 'private', 'secure', 'tor']
            hosting_indicators = ['hosting', 'server', 'cloud', 'datacenter', 'amazon', 'google', 'microsoft', 'digital ocean']
            
            is_vpn = any(indicator in f"{org_text} {asn_text}" for indicator in vpn_indicators)
            is_datacenter = any(indicator in f"{org_text} {asn_text}" for indicator in hosting_indicators)
            
            return {
                'provider': 'ipapi.co',
                'ip': data.get('ip'),
                'country': data.get('country_name'),
                'region': data.get('region'),
                'city': data.get('city'),
                'timezone': data.get('timezone'),
                'isp': data.get('org'),
                'asn': data.get('asn'),
                'proxy': False,
                'datacenter': is_datacenter,
                'vpn': is_vpn,
                'mobile': False,
                'success': True
            }
        except Exception as e:
            _logger.error(f"❌ IPapi.co falló: {str(e)}")
            raise
    
    def _check_with_ipapi_is(self, user_ip):
        """API 3: IPapi.is - 1000/mes gratis"""
        try:
            api_url = f"https://api.ipapi.is/?q={user_ip}"
            
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            
            data = response.json()
            
            location = data.get('location', {})
            company = data.get('company', {})
            security = data.get('security', {})
            
            return {
                'provider': 'ipapi.is',
                'ip': data.get('ip'),
                'country': location.get('country'),
                'region': location.get('state'),
                'city': location.get('city'),
                'timezone': location.get('timezone'),
                'isp': company.get('name'),
                'asn': data.get('asn', {}).get('asn'),
                'proxy': security.get('proxy', False),
                'datacenter': company.get('type') == 'hosting',
                'vpn': security.get('vpn', False),
                'mobile': False,
                'success': True
            }
        except Exception as e:
            _logger.error(f"❌ IPapi.is falló: {str(e)}")
            raise
    
    def _check_ip_and_flags(self, user_ip, timezone=None):
        """
        Método auxiliar para ser llamado desde los modelos.
        Realiza la verificación de la IP y devuelve las banderas de seguridad.
        """
        _logger.info(f"🌐 Verificando IP: {user_ip} desde el modelo.")
        
        # IPs locales/privadas - no verificar
        if user_ip.startswith(('127.', '192.168.', '10.', '172.')):
            return {
                'vpn_detectado': False,
                'proxy_detectado': False,
                'datacenter_detectado': False,
                'timezone_mismatch': False,
            }

        ip_info = self._get_cached_result(user_ip)
        if not ip_info:
            api_used = "none"
            try:
                ip_info = self._check_with_ipapi_is(user_ip)
                api_used = 'ipapi.is'
            except Exception as e1:
                _logger.warning(f"❌ Fallo al verificar con IPapi.is: {e1}")
                try:
                    ip_info = self._check_with_ipapi_co(user_ip)
                    api_used = 'ipapi.co'
                except Exception as e2:
                    _logger.warning(f"❌ Fallo al verificar con IPapi.co: {e2}")
                    try:
                        ip_info = self._check_with_ipapi_com(user_ip)
                        api_used = 'ip-api.com'
                    except Exception as e3:
                        _logger.warning(f"❌ Fallo al verificar con IP-API.com: {e3}")
                        ip_info = {'success': False, 'vpn': False, 'proxy': False, 'datacenter': False}
            
            if ip_info and ip_info.get('success'):
                self._cache_result(user_ip, ip_info)
                _logger.info(f"✅ Verificación exitosa con {api_used} para IP: {user_ip}")
            else:
                _logger.error(f"❌ Todas las APIs fallaron para IP: {user_ip}")

        vpn_detectado = ip_info.get('vpn', False)
        proxy_detectado = ip_info.get('proxy', False)
        datacenter_detectado = ip_info.get('datacenter', False)
        timezone_mismatch = False # Considera si quieres implementar esta lógica o dejarla en False
        
        return {
            'vpn_detectado': vpn_detectado,
            'proxy_detectado': proxy_detectado,
            'datacenter_detectado': datacenter_detectado,
            'timezone_mismatch': timezone_mismatch,
        }

    @http.route('/check/ipdetective', type='json', auth="user", methods=['POST'])
    def check_ip_endpoint(self, timezone=None):
        """Endpoint para la validación de IP (para uso con clientes JS si es necesario)"""
        user_ip = "unknown"
        if hasattr(request, 'httprequest'):
            user_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
            if user_ip and ',' in user_ip:
                user_ip = user_ip.split(',')[0].strip()
            if not user_ip:
                user_ip = request.httprequest.environ.get('HTTP_X_REAL_IP')
            if not user_ip:
                user_ip = request.httprequest.remote_addr
        
        flags = self._check_ip_and_flags(user_ip, timezone)
        
        # Almacenar los resultados en la sesión para uso posterior (opcional, pero útil)
        request.session['vpn_detectado'] = flags.get('vpn_detectado')
        request.session['proxy_detectado'] = flags.get('proxy_detectado')
        request.session['datacenter_detectado'] = flags.get('datacenter_detectado')
        request.session['timezone_mismatch'] = flags.get('timezone_mismatch')

        return {'success': True, 'flags': flags}