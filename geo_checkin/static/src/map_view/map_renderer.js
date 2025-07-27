// /** @odoo-module @geo_checkin/map_view/map_renderer **/

// import { MapRenderer } from "@web_map/map_view/map_renderer";
// import { patch } from "@web/core/utils/patch";
// import { _t } from "@web/core/l10n/translation";
// import { useService } from "@web/core/utils/hooks"; // Necesitas importar useService para usar el servicio ORM

// patch(MapRenderer.prototype, {
//     // Agrega el método setup para inicializar los servicios
//     setup() {
//         super.setup();
//         this.orm = useService("orm"); // Servicio ORM para llamar a métodos Python
//         this.action = useService("action"); // Servicio de acción para manejar las acciones devueltas por Odoo
//         this.notification = useService("notification"); // Servicio de notificaciones para dar feedback al usuario
//     },

//     /**
//      * Sobreescribe el método createMarkerPopup para agregar tu botón.
//      */
//     createMarkerPopup(markerInfo, latLongOffset = 0) {
//         const popup = super.createMarkerPopup(markerInfo, latLongOffset);
//         const popupContentElement = popup.getElement();
//         const popupButtonsContainer = popupContentElement.querySelector(".o-map-renderer--popup-buttons");

//         if (popupButtonsContainer) {
//             const myButton = document.createElement("button");
//             myButton.className = "btn btn-primary o-map-renderer--popup-buttons-my-button ms-2";
//             myButton.textContent = _t("Checkin"); // Texto del botón

//             myButton.addEventListener("click", () => {
//                 this.onMyButtonClick(markerInfo); // Llama a tu manejador de clic
//             });

//             popupButtonsContainer.appendChild(myButton);
//         }

//         return popup;
//     },

//     /**
//      * Maneja el clic en "Checkin".
//      * Llama directamente al método 'get_location_button' en el backend.
//      */
//     async onMyButtonClick(markerInfo) {
//         console.log("¡Checkin fue clicado!");
//         console.log("Información del registro asociado:", markerInfo.record);

//         if (!markerInfo.record || !markerInfo.record.id) {
//             this.notification.add(_t("No se pudo obtener la información de la tarea para realizar el check-in."), {
//                 type: "danger",
//             });
//             return;
//         }

//         try {
//             // Llama al método 'get_location_button' en el modelo 'project.task'
//             const result = await this.orm.call(
//                 'project.task', // Modelo
//                 'get_location_button', // Método Python a llamar
//                 [markerInfo.record.id] // Argumentos: El ID de la tarea
//             );

//             // El método 'get_location_button' en Python devuelve una acción de cliente.
//             // Necesitamos ejecutar esa acción en el frontend.
//             if (result && result.type === 'ir.actions.client') {
//                 this.action.doAction(result);
//             } else if (result) {
//                 // Si el método Python devuelve un resultado diferente, puedes manejarlo aquí.
//                 // Por ejemplo, si devuelve un diccionario con un mensaje:
//                 this.notification.add(result.message || _t("Acción de check-in iniciada con éxito."), {
//                     type: "success",
//                     sticky: false,
//                 });
//             }

//         } catch (error) {
//             console.error("Error al llamar al método get_location_button:", error);
//             this.notification.add(error.message || _t("Ocurrió un error al intentar iniciar el check-in."), {
//                 type: "danger",
//                 sticky: true,
//             });
//         }
//     },
// });

/** @odoo-module @geo_checkin/map_view/map_renderer **/

import { registry } from "@web/core/registry"; 
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// Seguiremos intentando obtener MapRenderer del registry, es la mejor práctica.
// (Asegúrate de haber probado y encontrado la clave correcta con el comando de consola)
const MapRenderer = registry.category("views").get("map").Renderer; // Reemplaza "map" con la clave exacta que encuentres.

patch(MapRenderer.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    },

    // El método createMarkerPopup ya NO necesita ser sobreescrito para añadir el botón.
    // Solo necesitamos el método que se llama desde el XML.

    /**
     * Maneja el clic en "Checkin" desde el botón del QWeb.
     * La 'target' es el record asociado al popup.
     */
    async onCheckinButtonClick(ev) {
        // Acceder a la información del registro desde 'this.props.record'
        // El 'markerInfo' que usabas antes ahora sería el 'record' en las props del popup
        const record = this.props.record; // 'this' aquí se refiere a la instancia del MapRenderer o el componente que renderiza el popup.

        console.log("¡Checkin fue clicado desde XML!");
        console.log("Información del registro asociado:", record);

        if (!record || !record.id) {
            this.notification.add(_t("No se pudo obtener la información de la tarea para realizar el check-in."), {
                type: "danger",
            });
            return;
        }

        try {
            const result = await this.orm.call(
                'project.task', // Modelo
                'get_location_button', // Método Python a llamar
                [record.id] // Argumentos: El ID de la tarea
            );

            if (result && result.type === 'ir.actions.client') {
                this.action.doAction(result);
            } else if (result) {
                this.notification.add(result.message || _t("Acción de check-in iniciada con éxito."), {
                    type: "success",
                    sticky: false,
                });
            }

        } catch (error) {
            console.error("Error al llamar al método get_location_button:", error);
            this.notification.add(error.message || _t("Ocurrió un error al intentar iniciar el check-in."), {
                type: "danger",
                sticky: true,
            });
        }
    },
});