/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { whenReady } from "@odoo/owl";

// Ejecutar cuando el DOM esté listo
whenReady(() => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    // Usar el servicio RPC optimizado de Odoo 18
    rpc("/check/ipdetective", {
        timezone: timezone
    }, {
        // Opciones adicionales para Odoo 18
        silent: true, // No mostrar spinner de loading
        timeout: 10000 // Timeout de 10 segundos
    }).then(function (data) {
        if (!data) {
            console.warn("No se recibió respuesta del servidor IPDetective");
            return;
        }

        if (data.error) {
            console.warn("Error consultando IPDetective:", data.error);
            return;
        }

        // Verificar si hay indicios de VPN/Proxy
        const hasSecurityIssues = data.vpn || data.proxy || data.datacenter || data.timezone_mismatch;
        
        if (hasSecurityIssues) {
            // Usar una notificación más moderna en lugar de alert
            const notification = document.createElement('div');
            notification.className = 'alert alert-warning alert-dismissible fade show position-fixed';
            notification.style.cssText = `
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            `;
            notification.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fa fa-exclamation-triangle me-2"></i>
                    <div>
                        <strong>⚠️ Conexión sospechosa detectada</strong><br>
                        <small>Se detectó posible uso de VPN, proxy o zona horaria manipulada.</small>
                    </div>
                    <button type="button" class="btn-close ms-2" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto-remover después de 8 segundos
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 8000);
            
            console.warn("🔒 Conexión sospechosa:", {
                vpn: data.vpn,
                proxy: data.proxy,
                datacenter: data.datacenter,
                timezone_mismatch: data.timezone_mismatch,
                ip: data.ip
            });
        } else {
            console.log("✅ Conexión segura verificada:", {
                ip: data.ip,
                country: data.country,
                timezone: data.timezone
            });
        }
    }).catch(function (error) {
        // Manejo de errores mejorado
        console.error("Error verificando IP:", error);
        
        // Solo mostrar error si no es un problema de red común
        if (error.type !== 'network' && error.status !== 0) {
            console.warn("No se pudo verificar la seguridad de la conexión IP");
        }
    });
});