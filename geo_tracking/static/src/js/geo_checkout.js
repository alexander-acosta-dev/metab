/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

// Función auxiliar para obtener la IP pública
async function getPublicIpAddress() {
    try {
        const response = await browser.fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        return data.ip;
    } catch (error) {
        console.error("No se pudo obtener la IP pública desde api.ipify.org:", error);
        return null;
    }
}

// Función de acción para manejar el checkout
async function getGeolocationFromBrowserCheckout(env, action) {
    const { task_id } = action.params || {};
    const notification = env.services.notification;
    const orm = env.services.orm;
    const actionService = env.services.action;

    console.log("GeolocationCheckoutAction iniciada con task_id:", task_id);

    if (!task_id) {
        notification.add(_t("Error: No se encontró el ID de la tarea."), { type: 'danger', sticky: true });
        return;
    }

    if (!navigator.geolocation) {
        notification.add(_t("Tu navegador no soporta geolocalización."), { type: 'danger', sticky: true });
        return;
    }

    notification.add(_t("Obteniendo ubicación para check-out..."), { type: 'info' });

    const options = {
        enableHighAccuracy: true,
        timeout: 30000,
        maximumAge: 60000
    };

    try {
        const publicIp = await getPublicIpAddress();
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const location_data = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        ip: publicIp, // Enviar la IP al servidor
                        timezone,
                    };

                    console.log("Ubicación de check-out obtenida:", location_data);

                    try {
                        const result = await orm.call(
                            'project.task',
                            'get_checkout_location',
                            [task_id, location_data]
                        );

                        if (result && result.error_message) {
                            notification.add(result.error_message, { type: 'danger', sticky: true });
                        } else {
                            const message = _t("Check-out realizado con éxito. Duración: %s, Distancia: %s km.")
                                .replace("%s", result.duration)
                                .replace("%s", result.distance_km);
                            notification.add(message, { type: 'success' });
                            
                            actionService.doAction({ type: 'ir.actions.act_window_close' }).then(() => {
                                window.location.reload();
                            });
                        }
                        resolve();
                    } catch (error) {
                        const errorMessage = error.message?.data?.message || _t("Error al procesar el check-out.");
                        console.error("Error en check-out:", error);
                        notification.add(errorMessage, { type: 'danger', sticky: true });
                        reject(error);
                    }
                },
                (error) => {
                    let message;
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            message = _t("Acceso a la ubicación denegado. Por favor, permite el acceso a la ubicación en tu navegador.");
                            break;
                        case error.POSITION_UNAVAILABLE:
                            message = _t("La ubicación no está disponible. Intenta nuevamente.");
                            break;
                        case error.TIMEOUT:
                            message = _t("Tiempo de espera agotado al obtener la ubicación. Intenta nuevamente.");
                            break;
                        default:
                            message = _t("Error desconocido al obtener la ubicación.");
                            break;
                    }
                    console.error("Error de geolocalización en check-out:", error);
                    notification.add(message, { type: 'danger', sticky: true });
                    reject(error);
                },
                options
            );
        });
    } catch (error) {
        console.error("Error al obtener la IP pública:", error);
        notification.add(_t("Error al obtener la dirección IP para el check-out."), { type: 'danger', sticky: true });
    }
}

registry.category("actions").add("get_geolocation_from_browser_checkout", getGeolocationFromBrowserCheckout);