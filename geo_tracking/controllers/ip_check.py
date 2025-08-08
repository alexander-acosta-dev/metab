@http.route('/check/ipdetective', type='json', auth="user", methods=['POST'])
def check_ip_endpoint(self, **post):
    timezone = post.get('timezone')
    user_ip = post.get('client_ip')  # ✅ Usar IP del cliente si está disponible

    if not user_ip:
        if hasattr(request, 'httprequest'):
            user_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
            if user_ip and ',' in user_ip:
                user_ip = user_ip.split(',')[0].strip()
            if not user_ip:
                user_ip = request.httprequest.environ.get('HTTP_X_REAL_IP')
            if not user_ip:
                user_ip = request.httprequest.remote_addr

    if not user_ip or user_ip == "unknown":
        _logger.warning("❗ No se pudo detectar la IP del usuario.")
        return {'success': False, 'error': 'No se pudo detectar la IP'}

    ip_info = self._get_ip_info(user_ip)

    ip_timezone = (ip_info.get('timezone') or '').strip().lower()
    client_timezone = (timezone or '').strip().lower()
    timezone_mismatch = ip_timezone != client_timezone and client_timezone != ""

    _logger.info(f"🌐 Comparación de zonas horarias - IP: {ip_timezone} | Cliente: {client_timezone} | Mismatch: {timezone_mismatch}")

    flags = {
        'vpn_detectado': ip_info.get('vpn', False),
        'proxy_detectado': ip_info.get('proxy', False),
        'datacenter_detectado': ip_info.get('datacenter', False),
        'timezone_mismatch': timezone_mismatch
    }

    # Guardar en sesión
    request.session['vpn_detectado'] = flags['vpn_detectado']
    request.session['proxy_detectado'] = flags['proxy_detectado']
    request.session['datacenter_detectado'] = flags['datacenter_detectado']
    request.session['timezone_mismatch'] = flags['timezone_mismatch']

    return {
        'success': True,
        'ip': user_ip,
        'flags': flags,
        'provider': ip_info.get('provider'),
        'country': ip_info.get('country'),
        'region': ip_info.get('region'),
        'city': ip_info.get('city'),
        'geo_timezone': ip_info.get('timezone'),
        'browser_timezone': timezone,
        'isp': ip_info.get('isp'),
    }