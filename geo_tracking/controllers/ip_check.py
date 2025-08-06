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
        # Limpiar cache antiguo (mantener solo últimas 100 IPs)
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
            
            # Detección mejorada de VPN
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
            
            # Detección VPN/Datacenter mejorada
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
                'proxy': False,  # IPapi.co no reporta proxy directamente
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
    
    @http.route('/check/ipdetective', type='json', auth="user", methods=['POST'])
    def check_ip(self, timezone=None):
        try:
            # Obtener IP del usuario
            user_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
            if user_ip and ',' in user_ip:
                user_ip = user_ip.split(',')[0].strip()
            
            if not user_ip:
                user_ip = request.httprequest.environ.get('HTTP_X_REAL_IP')
            if not user_ip:
                user_ip = request.httprequest.remote_addr
            
            # IPs locales/privadas - no verificar
            if user_ip.startswith(('127.', '192.168.', '10.', '172.')):
                return {
                    'ip': user_ip,
                    'status': 'local_ip',
                    'vpn': False,
                    'proxy': False,
                    'datacenter': False,
                    'timezone_mismatch': False,
                    'message': 'IP local/privada - verificación omitida'
                }
            
            _logger.info(f"🔍 Verificando IP: {user_ip}")
            
            # Verificar cache primero
            cached_result = self._get_cached_result(user_ip)
            if cached_result:
                # Actualizar timezone check con datos actuales
                cached_result['browser_timezone'] = timezone
                cached_result['timezone_mismatch'] = (
                    cached_result.get('geo_timezone') != timezone 
                    if cached_result.get('geo_timezone') and timezone else False
                )
                return cached_result
            
            # Lista de APIs para intentar
            api_methods = [
                self._check_with_ipapi_com,    # Más rápida y confiable
                self._check_with_ipapi_is,     # Mejor detección de seguridad
                self._check_with_ipapi_co      # Backup confiable
            ]
            
            # Intentar cada API
            last_error = None
            for i, api_method in enumerate(api_methods, 1):
                try:
                    _logger.info(f"🔄 Intentando API {i}/3: {api_method.__name__}")
                    
                    data = api_method(user_ip)
                    
                    # Análisis de timezone
                    geo_timezone = data.get('timezone', '')
                    browser_timezone = timezone or ''
                    timezone_mismatch = geo_timezone != browser_timezone if geo_timezone and browser_timezone else False
                    
                    # Resultado final
                    result = {
                        'ip': data.get('ip', user_ip),
                        'country': data.get('country'),
                        'region': data.get('region'),
                        'city': data.get('city'),
                        'isp': data.get('isp'),
                        'provider': data.get('provider'),
                        'geo_timezone': geo_timezone,
                        'browser_timezone': browser_timezone,
                        'timezone_mismatch': timezone_mismatch,
                        'vpn': data.get('vpn', False),
                        'proxy': data.get('proxy', False),
                        'datacenter': data.get('datacenter', False),
                        'mobile': data.get('mobile', False),
                        'status': 'success'
                    }
                    
                    # Guardar en cache
                    self._cache_result(user_ip, result)
                    
                    _logger.info(f"✅ Éxito con {data.get('provider')}: VPN={result['vpn']}, Proxy={result['proxy']}, DC={result['datacenter']}")
                    return result
                    
                except Exception as e:
                    last_error = str(e)
                    _logger.warning(f"⚠️ API {i} falló: {e}")
                    continue
            
            # Si todas fallaron
            error_msg = f"Todas las APIs fallaron. Último error: {last_error}"
            _logger.error(f"💥 {error_msg}")
            return {
                'error': error_msg,
                'ip': user_ip,
                'status': 'api_error'
            }
            
        except Exception as e:
            error_msg = f"Error crítico: {str(e)}"
            _logger.error(f"🚨 {error_msg}")
            return {
                'error': error_msg,
                'status': 'critical_error'
            }