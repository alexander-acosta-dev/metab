/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
import { browser } from "@web/core/browser/browser";

// Función de acción cliente corregida para check-in
async function getGeolocationClientAction(env, action) {
    const { task_id } = action.params || {};
    const orm = env.services.orm;
    const notification = env.services.notification;

    if (!task_id) {
        notification.add(_t("Error: No se encontró el ID de la tarea."), { type: 'danger', sticky: true });
        return;
    }

    notification.add(_t("Obteniendo su ubicación actual..."), { type: 'info' });

    try {
        const publicIp = await getPublicIpAddress();
        console.log("IP pública obtenida:", publicIp);

        // Si la IP no se pudo obtener, se continua, pero se registrará en el servidor
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        if (navigator.geolocation) {
            await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    async (position) => {
                        const { latitude, longitude, accuracy } = position.coords;
                        console.log("Ubicación obtenida:", latitude, longitude, "Precisión:", accuracy);

                        try {
                            const result = await orm.call(
                                'project.task',
                                'get_location',
                                [task_id, {
                                    latitude,
                                    longitude,
                                    accuracy,
                                    ip: publicIp, // Enviar la IP al servidor
                                    timezone,
                                }]
                            );
                            
                            handleServerResponse(result, notification, env.services.action);
                            resolve();
                        } catch (error) {
                            handleRpcError(error, notification);
                            reject(error);
                        }
                    },
                    (error) => {
                        handleGeolocationError(error, notification);
                        reject(error);
                    },
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                );
            });
        } else {
            notification.add(_t("Tu navegador no soporta la geolocalización."), { type: 'danger', sticky: true });
        }
    } catch (error) {
        console.error("Error al obtener la IP pública:", error);
        notification.add(_t("Error al obtener la dirección IP."), { type: 'danger', sticky: true });
    }
}

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

// Función auxiliar para manejar la respuesta del servidor
function handleServerResponse(result, notification, actionService) {
    if (result.type === 'ir.actions.client' && result.tag === 'display_notification') {
        const params = result.params || {};
        notification.add(params.message || _t("Error al registrar la ubicación"), {
            type: params.type || 'danger',
            sticky: params.sticky !== undefined ? params.sticky : true,
        });
    } else {
        notification.add(result.message || _t("Ubicación registrada con éxito"), {
            type: 'success',
        });
    }

    if (!(result.type === 'ir.actions.client' && result.tag === 'display_notification' && (result.params?.type === 'danger' || result.params?.type === 'warning'))) {
        actionService.doAction({ type: 'ir.actions.act_window_close' }).then(() => {
            window.location.reload();
        });
    }
}

// Función auxiliar para manejar errores de RPC (server)
function handleRpcError(error, notification) {
    const errorMessage = error.message?.data?.message || _t("Error al registrar la ubicación.");
    console.error("Error al registrar la ubicación en Odoo:", error);
    notification.add(errorMessage, { type: 'danger', sticky: true });
}

// Función auxiliar para manejar errores de geolocalización (navegador)
function handleGeolocationError(error, notification) {
    let errorMessage = _t("Error desconocido al obtener la ubicación.");
    switch(error.code) {
        case error.PERMISSION_DENIED:
            errorMessage = _t("Permiso denegado para acceder a la ubicación. Asegúrate de que tu navegador permita la geolocalización para este sitio.");
            break;
        case error.POSITION_UNAVAILABLE:
            errorMessage = _t("La información de ubicación no está disponible.");
            break;
        case error.TIMEOUT:
            errorMessage = _t("La solicitud para obtener la ubicación ha caducado.");
            break;
    }
    console.error("Error al obtener la ubicación del navegador:", error);
    notification.add(errorMessage, { type: 'danger', sticky: true });
}

registry.category('actions').add('get_geolocation_from_browser', getGeolocationClientAction, { force: true });