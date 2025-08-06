/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";

// Función de acción cliente corregida
function getGeolocationClientAction(env, action) {
    const { task_id } = action.params || {};
    const orm = env.services.orm;
    const notification = env.services.notification;
    
    notification.add(_t("Obteniendo su ubicación actual..."), { type: 'info' });

    return new Promise((resolve) => {
        // Verificar si el navegador soporta la API de Geolocation
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                // Función de éxito
                async (position) => {
                    const { latitude, longitude, accuracy } = position.coords;
                    console.log("Ubicación obtenida del navegador:", latitude, longitude, "Precisión:", accuracy);

                    try {
                        // Llamar al método Python 'get_location'
                        const result = await orm.call(
                            'project.task',
                            'get_location',
                            [task_id, { latitude, longitude, accuracy }]
                        );

                        if(result.type === 'ir.actions.client' && result.tag === 'display_notification') {
                            const params = result.params || {};
                            notification.add(params.message || _t("Error al registrar la ubicación"),{
                                type: params.type || 'danger',
                                sticky: params.sticky !== undefined ? params.sticky : true,
                            });
                        }else{
                            notification.add(result.message || _t("Ubicación registrada con éxito"),{
                                type: 'success',
                            });
                        }
                        
                        if(!(result.type === 'ir.actions.client' && result.tag === 'display_notification' && (result.params?.type === 'danger' || result.params?.type === 'warning'))) {
                            env.services.action.doAction({
                                type: 'ir.actions.act_window_close'
                            }).then(() => {    
                                window.location.reload();
                            });
                        }

                        resolve();
                    } catch (error) {
                        console.error("Error al registrar la ubicación en Odoo:", error);
                        notification.add(
                            error.message?.data?.message || _t("Error al registrar la ubicación."), 
                            {
                                type: 'danger',
                                sticky: true
                            }
                        );
                        resolve();
                    }
                },
                // Función de error
                (error) => {
                    console.error("Error al obtener la ubicación del navegador:", error);
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
                    
                    notification.add(errorMessage, {
                        type: 'danger',
                        sticky: true
                    });
                    resolve();
                },
                // Opciones para la solicitud de geolocalización
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        } else {
            notification.add(_t("Tu navegador no soporta la geolocalización."), {
                type: 'danger',
                sticky: true
            });
            resolve();
        }
    });
}

// Registrar la acción cliente forzando el reemplazo si existe
registry.category('actions').add('get_geolocation_from_browser', getGeolocationClientAction, { force: true });

// Extender el FormController para mejorar la experiencia
export class GeoCheckinFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async executeActionButton(action, activeIds, viewId, modelName) {
        // Si es nuestra acción específica, asegurar que tenemos el task_id correcto
        if (action.tag === 'get_geolocation_from_browser') {
            const taskId = this.model.root.resId;
            if (taskId) {
                // Actualizar los parámetros de la acción con el ID de la tarea
                action.params = { ...action.params, task_id: taskId };
            }
        }
        
        return super.executeActionButton(action, activeIds, viewId, modelName);
    }
}

// Registrar el controlador personalizado con verificación
try {
    const formView = registry.category("views").get("form");
    if (formView && !registry.category("views").contains("geo_checkin_form")) {
        registry.category("views").add("geo_checkin_form", {
            ...formView,
            Controller: GeoCheckinFormController,
        });
    }
} catch (error) {
    console.error("Error registrando geo_checkin_form:", error);
}