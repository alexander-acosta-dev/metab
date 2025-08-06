odoo.define('custom.ip_check', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    document.addEventListener("DOMContentLoaded", function () {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        ajax.jsonRpc("/check/ipdetective", 'call', {
            timezone: timezone
        }).then(function (data) {
            if (data.error) {
                console.warn("Error consultando IPDetective:", data.error);
                return;
            }

            if (data.vpn || data.proxy || data.datacenter || data.timezone_mismatch) {
                alert("⚠️ Se detectó posible uso de VPN, proxy o zona horaria manipulada.\nPor favor verifica tu conexión.");
            } else {
                console.log("✅ IP segura:", data.ip);
            }
        });
    });
});