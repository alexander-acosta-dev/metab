/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Función moderna para manejar el checkout
// El objeto 'env' ya contiene todos los servicios necesarios.
function getGeolocationFromBrowserCheckout(env, action) {
    const { task_id } = action.params || {};

    // Obtener los servicios dentro de la función de acción
    const notification = env.services.notification;
    const orm = env.services.orm;
    const actionService = env.services.action;

    console.log("GeolocationCheckoutAction iniciada con task_id:", task_id);

    if (!task_id) {
        notification.add(_t("Error: No se encontró el ID de la tarea."), {
            type: 'danger',
            sticky: true
        });
        return Promise.resolve(); // Resuelve la promesa para evitar errores
    }

    if (!navigator.geolocation) {
        notification.add(_t("Tu navegador no soporta geolocalización."), {
            type: 'danger',
            sticky: true
        });
        return Promise.resolve();
    }

    notification.add(_t("Obteniendo ubicación para check-out..."), {
        type: 'info',
        sticky: false
    });

    const options = {
        enableHighAccuracy: true,
        timeout: 30000,
        maximumAge: 60000
    };

    return new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const location_data = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                };

                console.log("Ubicación de check-out obtenida:", location_data);

                try {
                    const result = await orm.call(
                        'project.task',
                        'get_checkout_location',
                        [task_id, location_data]
                    );

                    // Revisamos si el resultado de Python contiene un mensaje de error
                    if (result && result.error_message) {
                        notification.add(result.error_message, {
                            type: 'danger',
                            sticky: true
                        });
                        resolve();
                    } else {
                        // Todo OK, mostramos el mensaje de éxito
                        const message = _t("Check-out realizado con éxito. Duración: %s, Distancia: %s km.")
                                        .replace("%s", result.duration)
                                        .replace("%s", result.distance_km);

                        notification.add(message, {
                            type: 'success',
                            sticky: false
                        });
                        
                        // Recargar la vista actual usando el servicio de acción
                        actionService.doAction({
                            type: 'ir.actions.act_window_close'
                        }).then(() => {
                            window.location.reload();
                            resolve();
                        });
                    }                   
                } catch (error) {
                    // Si la llamada al ORM falló con un raise de Python
                    console.error("Error en check-out:", error);
                    const errorMessage = error.message?.data?.message || _t("Error al procesar el check-out.");
                    notification.add(errorMessage, {
                        type: 'danger',
                        sticky: true
                    });
                    resolve();
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
                notification.add(message, {
                    type: 'danger',
                    sticky: true
                });
                resolve();
            },
            options
        );
    });
}

// Registrar la acción
registry.category("actions").add("get_geolocation_from_browser_checkout", getGeolocationFromBrowserCheckout);