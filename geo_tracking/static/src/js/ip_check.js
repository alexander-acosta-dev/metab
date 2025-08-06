/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { whenReady } from "@odoo/owl";

// Ejecutar cuando el DOM esté listo
whenReady(() => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    console.log("🚀 Iniciando verificación de seguridad IP con timezone:", timezone);
    
    // Usar el servicio RPC de Odoo 18
    rpc("/check/ipdetective", {
        timezone: timezone
    }).then(function (data) {
        console.log("📡 Respuesta completa del servidor:", data);
        
        // Verificar si la respuesta es válida
        if (!data || typeof data !== 'object') {
            console.warn("⚠️ Respuesta inválida del servidor:", data);
            return;
        }

        // Manejar errores de la API
        if (data.error) {
            console.warn("❌ Error en verificación IP:", data.error);
            
            // Mostrar notificación de error de sistema (opcional)
            if (data.status === 'critical_error') {
                showNotification('error', '🚨 Error crítico de verificación', data.error);
            }
            return;
        }

        // Manejar IP local
        if (data.status === 'local_ip') {
            console.log("🏠 IP local detectada:", data.message);
            return;
        }

        // Verificar si hay indicios de VPN/Proxy/Datacenter
        const hasSecurityIssues = data.vpn || data.proxy || data.datacenter || data.timezone_mismatch;
        
        console.log("🔍 Análisis de seguridad completo:", {
            provider: data.provider,
            ip: data.ip,
            country: data.country,
            region: data.region,
            city: data.city,
            isp: data.isp,
            vpn: data.vpn,
            proxy: data.proxy,
            datacenter: data.datacenter,
            mobile: data.mobile,
            timezone_mismatch: data.timezone_mismatch,
            geo_timezone: data.geo_timezone,
            browser_timezone: data.browser_timezone
        });
        
        if (hasSecurityIssues) {
            // Determinar nivel de riesgo
            let riskLevel = 'warning';
            let riskCount = 0;
            if (data.vpn) riskCount++;
            if (data.proxy) riskCount++;
            if (data.datacenter) riskCount++;
            if (data.timezone_mismatch) riskCount++;
            
            if (riskCount >= 2) riskLevel = 'danger';
            
            // Crear lista de issues detectados
            let issues = [];
            if (data.vpn) issues.push('🔒 VPN');
            if (data.proxy) issues.push('🛡️ Proxy');
            if (data.datacenter) issues.push('🏢 Datacenter');
            if (data.timezone_mismatch) issues.push('🌍 Zona horaria');
            
            // Crear notificación de advertencia
            const notification = document.createElement('div');
            notification.className = `alert alert-${riskLevel} alert-dismissible fade show position-fixed`;
            notification.style.cssText = `
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 450px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.4);
                border-left: 5px solid ${riskLevel === 'danger' ? '#dc3545' : '#ffc107'};
                animation: slideIn 0.5s ease-out;
            `;
            
            const icon = riskLevel === 'danger' ? '🚨' : '⚠️';
            const title = riskLevel === 'danger' ? 'Conexión de alto riesgo' : 'Conexión sospechosa detectada';
            
            notification.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="me-3 mt-1">
                        <i class="fa fa-shield-alt text-${riskLevel}" style="font-size: 1.2em;"></i>
                    </div>
                    <div class="flex-grow-1">
                        <strong>${icon} ${title}</strong><br>
                        <small class="text-muted">Detectado: ${issues.join(', ')}</small><br>
                        <small class="text-muted">📍 ${data.country || 'País desconocido'} • ${data.city || 'Ciudad desconocida'}</small><br>
                        <small class="text-muted">🌐 ${data.ip} • ${data.isp || 'ISP desconocido'}</small><br>
                        <small class="text-muted mt-1 d-block">🔗 Fuente: ${data.provider || 'API múltiple'}</small>
                    </div>
                    <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto-remover después de 15 segundos (más tiempo para leer)
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.animation = 'slideOut 0.5s ease-in';
                    setTimeout(() => notification.remove(), 500);
                }
            }, 15000);
            
            console.warn("🔒 CONEXIÓN SOSPECHOSA DETECTADA:", {
                riskLevel: riskLevel,
                ip: data.ip,
                location: `${data.city}, ${data.region}, ${data.country}`,
                issues: issues,
                details: {
                    vpn: data.vpn,
                    proxy: data.proxy,
                    datacenter: data.datacenter,
                    timezone_mismatch: data.timezone_mismatch,
                    geo_tz: data.geo_timezone,
                    browser_tz: data.browser_timezone,
                    isp: data.isp,
                    provider: data.provider
                }
            });
            
            // Opcional: Enviar evento personalizado para otros sistemas
            window.dispatchEvent(new CustomEvent('suspiciousConnection', {
                detail: {
                    riskLevel: riskLevel,
                    data: data,
                    issues: issues
                }
            }));
            
        } else {
            console.log("✅ CONEXIÓN SEGURA VERIFICADA:", {
                ip: data.ip,
                location: `${data.city}, ${data.region}, ${data.country}`,
                isp: data.isp,
                mobile: data.mobile,
                geo_timezone: data.geo_timezone,
                browser_timezone: data.browser_timezone,
                provider: data.provider
            });
            
            // Opcional: Mostrar confirmación discreta de seguridad
            if (window.location.hash.includes('debug') || localStorage.getItem('show_security_ok')) {
                showNotification('success', '✅ Conexión verificada', 
                    `IP segura desde ${data.country} (${data.provider})`);
            }
        }
        
    }).catch(function (error) {
        console.error("💥 Error completo verificando IP:", error);
        
        // Análisis detallado del error
        if (error.message) {
            if (error.message.includes("Extra data")) {
                console.error("🔧 Error de formato JSON del servidor. Verifica el controlador Python.");
            } else if (error.message.includes("Unexpected token")) {
                console.error("🔧 Respuesta del servidor no es JSON válido.");
            } else if (error.message.includes("404")) {
                console.error("🔧 Endpoint /check/ipdetective no encontrado. Verifica la ruta.");
            } else if (error.message.includes("500")) {
                console.error("🔧 Error interno del servidor. Revisa logs de Odoo.");
            } else {
                console.error("🔧 Error general:", error.message);
            }
        }
        
        // Solo mostrar error si es crítico
        if (error.message && !error.message.includes("404")) {
            showNotification('error', '🚨 Error de verificación', 
                'No se pudo verificar la seguridad de la conexión');
        }
    });
});

// Función auxiliar para mostrar notificaciones
function showNotification(type, title, message) {
    const typeClasses = {
        'success': 'alert-success',
        'warning': 'alert-warning', 
        'error': 'alert-danger',
        'info': 'alert-info'
    };
    
    const icons = {
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'error': 'fa-times-circle',
        'info': 'fa-info-circle'
    };
    
    const notification = document.createElement('div');
    notification.className = `alert ${typeClasses[type]} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.5s ease-out;
    `;
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fa ${icons[type]} me-2"></i>
            <div class="flex-grow-1">
                <strong>${title}</strong>
                ${message ? `<br><small>${message}</small>` : ''}
            </div>
            <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remover
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.5s ease-in';
            setTimeout(() => notification.remove(), 500);
        }
    }, 8000);
}

// CSS animations (inyectar una sola vez)
if (!document.getElementById('security-notifications-css')) {
    const style = document.createElement('style');
    style.id = 'security-notifications-css';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}