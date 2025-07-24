/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// Espera a que el módulo esté definido antes de parchar
odoo.define("geo_checkin.map_renderer_patch", function (require) {
    const { Component } = require("owl");
    const { MapRenderer } = require("web_map.map_view.map_renderer");

    patch(MapRenderer.prototype, {
        setup() {
            super.setup();
            this.orm = useService("orm");
            this.action = useService("action");
            this.notification = useService("notification");
        },

        createMarkerPopup(markerInfo, latLongOffset = 0) {
            const popup = super.createMarkerPopup(markerInfo, latLongOffset);
            const popupContentElement = popup.getElement();
            const popupButtonsContainer = popupContentElement.querySelector(".o-map-renderer--popup-buttons");

            if (popupButtonsContainer) {
                const myButton = document.createElement("button");
                myButton.className = "btn btn-primary o-map-renderer--popup-buttons-my-button ms-2";
                myButton.textContent = _t("Checkin");

                myButton.addEventListener("click", () => {
                    this.onMyButtonClick(markerInfo);
                });

                popupButtonsContainer.appendChild(myButton);
            }

            return popup;
        },

        async onMyButtonClick(markerInfo) {
            if (!markerInfo.record || !markerInfo.record.id) {
                this.notification.add(_t("No se pudo obtener la información de la tarea para realizar el check-in."), {
                    type: "danger",
                });
                return;
            }

            try {
                const result = await this.orm.call(
                    'project.task',
                    'get_location_button',
                    [markerInfo.record.id]
                );

                if (result && result.type === 'ir.actions.client') {
                    this.action.doAction(result);
                } else if (result) {
                    this.notification.add(result.message || _t("Acción de check-in iniciada con éxito."), {
                        type: "success",
                    });
                }

            } catch (error) {
                console.error("Error en check-in:", error);
                this.notification.add(_t("Ocurrió un error al intentar realizar el check-in."), {
                    type: "danger",
                    sticky: true,
                });
            }
        },
    });
});
