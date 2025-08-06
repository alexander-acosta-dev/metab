/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { whenReady } from "@odoo/owl";

// Ejecutar cuando el DOM esté listo
whenReady(() => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    console.log("Iniciando verificación IP con timezone:", timezone);
    
    // Usar el servicio RPC de Odoo 18
    rpc("/check/ipdetective", {
        timezone: timezone
    }).then(function (data) {
        console.log("Respuesta completa del servidor:", data);
        
        // Verificar si la respuesta es válida
        if (!data || typeof data !== 'object') {
            console.warn("Respuesta inválida del servidor IPDetective:", data);
            return;
        }

        if (data.error) {
            console.warn("Error consultando IPDetective:", data.error);
            return;
        }

        // Verificar si hay indicios de VPN/Proxy
        const hasSecurityIssues = data.vpn || data.proxy || data.datacenter || data.timezone_mismatch;
        
        console.log("Análisis de seguridad:", {
            ip: data.ip,
            vpn: data.vpn,
            proxy: data.proxy,
            datacenter: data.datacenter,
            timezone_mismatch: data.timezone_mismatch,
            geo_timezone: data.geo_timezone,
            browser_timezone: data.browser_timezone
        });
        
        if (hasSecurityIssues) {
            // Crear notificación de advertencia
            const notification = document.createElement('div');
            notification.className = 'alert alert-warning alert-dismissible fade show position-fixed';
            notification.style.cssText = `
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            `;
            
            let issues = [];
            if (data.vpn) issues.push('VPN');
            if (data.proxy) issues.push('Proxy');
            if (data.datacenter) issues.push('Datacenter');
            if (data.timezone_mismatch) issues.push('Zona horaria');
            
            notification.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fa fa-exclamation-triangle me-2 text-warning"></i>
                    <div>
                        <strong>⚠️ Conexión sospechosa detectada</strong><br>
                        <small>Detectado: ${issues.join(', ')}</small><br>
                        <small>IP: ${data.ip || 'Desconocida'}</small>
                    </div>
                    <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto-remover después de 10 segundos
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 10000);
            
            console.warn("🔒 Conexión sospechosa detectada:", {
                ip: data.ip,
                issues: issues,
                details: {
                    vpn: data.vpn,
                    proxy: data.proxy,
                    datacenter: data.datacenter,
                    timezone_mismatch: data.timezone_mismatch,
                    geo_tz: data.geo_timezone,
                    browser_tz: data.browser_timezone
                }
            });
        } else {
            console.log("✅ Conexión segura verificada:", {
                ip: data.ip,
                country: data.country,
                geo_timezone: data.geo_timezone,
                browser_timezone: data.browser_timezone
            });
        }
    }).catch(function (error) {
        console.error("Error completo verificando IP:", error);
        
        // Verificar diferentes tipos de error
        if (error.message) {
            if (error.message.includes("Extra data")) {
                console.error("Error de formato JSON del servidor. Verifica el controlador Python.");
            } else if (error.message.includes("Unexpected token")) {
                console.error("Respuesta del servidor no es JSON válido.");
            } else {
                console.error("Error general:", error.message);
            }
        }
    });
});