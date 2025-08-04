// /** @odoo-module **/

// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";
// import { _t } from "@web/core/l10n/translation";

// // Función moderna para manejar el checkout en lugar de clase
// function getGeolocationFromBrowserCheckout({ env }) {
//     const notification = useService("notification");
//     const orm = useService("orm");
//     const action = useService("action");

//     return {
//         async start(env, { task_id }) {
//             console.log("GeolocationCheckoutAction iniciada con task_id:", task_id);
            
//             if (!task_id) {
//                 notification.add(_t("Error: No se encontró el ID de la tarea."), {
//                     type: 'danger',
//                     sticky: true
//                 });
//                 return;
//             }

//             // Verificar si el navegador soporta geolocalización
//             if (!navigator.geolocation) {
//                 notification.add(_t("Tu navegador no soporta geolocalización."), {
//                     type: 'danger',
//                     sticky: true
//                 });
//                 return;
//             }

//             // Mostrar mensaje de carga
//             notification.add(_t("Obteniendo ubicación para check-out..."), {
//                 type: 'info',
//                 sticky: false
//             });

//             // Configurar opciones de geolocalización
//             const options = {
//                 enableHighAccuracy: true,
//                 timeout: 30000,
//                 maximumAge: 60000
//             };

//             // Obtener ubicación actual
//             navigator.geolocation.getCurrentPosition(
//                 async (position) => {
//                     await handleCheckoutLocationSuccess(position, task_id, notification, orm, action);
//                 },
//                 (error) => {
//                     handleCheckoutLocationError(error, notification);
//                 },
//                 options
//             );
//         },
//     };
// }

// async function handleCheckoutLocationSuccess(position, task_id, notification, orm, action) {
//     const location_data = {
//         latitude: position.coords.latitude,
//         longitude: position.coords.longitude,
//         accuracy: position.coords.accuracy
//     };

//     console.log("Ubicación de check-out obtenida:", location_data);

//     try {
//         const result = await orm.call(
//             'project.task',
//             'get_checkout_location',
//             [task_id, location_data]
//         );

//         if (result.message) {
//             notification.add(result.message, {
//                 type: 'success',
//                 sticky: false
//             });
//         }
        
//         // Recargar la vista actual
//         if (action && action.doAction) {
//             action.doAction('reload');
//         }
        
//     } catch (error) {
//         console.error("Error en check-out:", error);
//         notification.add(error.message || _t("Error al procesar el check-out."), {
//             type: 'danger',
//             sticky: true
//         });
//     }
// }

// function handleCheckoutLocationError(error, notification) {
//     let message;
    
//     switch(error.code) {
//         case error.PERMISSION_DENIED:
//             message = _t("Acceso a la ubicación denegado. Por favor, permite el acceso a la ubicación en tu navegador.");
//             break;
//         case error.POSITION_UNAVAILABLE:
//             message = _t("La ubicación no está disponible. Intenta nuevamente.");
//             break;
//         case error.TIMEOUT:
//             message = _t("Tiempo de espera agotado al obtener la ubicación. Intenta nuevamente.");
//             break;
//         default:
//             message = _t("Error desconocido al obtener la ubicación.");
//             break;
//     }

//     console.error("Error de geolocalización en check-out:", error);
    
//     notification.add(message, {
//         type: 'danger',
//         sticky: true
//     });
// }

// // Registrar la acción
// registry.category("actions").add("get_geolocation_from_browser_checkout", getGeolocationFromBrowserCheckout);


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

    return new Promise((resolve, reject) => {
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

                    notification.add(_t("Check-out realizado con éxito."), {
                        type: 'success',
                        sticky: false
                    });
                    
                    // Recargar la vista actual usando el servicio de acción
                    actionService.doAction({
                        type: 'ir.actions.act_window_close'
                    }).then(() => {
                        window.location.reload();
                    });
                    
                    resolve(result);

                } catch (error) {
                    console.error("Error en check-out:", error);
                    notification.add(error.message?.data?.message || _t("Error al procesar el check-out."), {
                        type: 'danger',
                        sticky: true
                    });
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
                notification.add(message, {
                    type: 'danger',
                    sticky: true
                });
                reject(error);
            },
            options
        );
    });
}

// Registrar la acción
registry.category("actions").add("get_geolocation_from_browser_checkout", getGeolocationFromBrowserCheckout);