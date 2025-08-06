/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";

document.addEventListener("DOMContentLoaded", function () {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    jsonrpc("/check/ipdetective", {
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
    }).catch(function (error) {
        console.error("Error en la consulta IP:", error);
    });
});