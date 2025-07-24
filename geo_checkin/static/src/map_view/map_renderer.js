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
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { whenReady } from "@web/core/utils/misc";

console.log("=== Iniciando Geo Checkin para Odoo 18 ===");

// En Odoo 18, usar whenReady para asegurar que todo esté cargado
whenReady(() => {
    console.log("Sistema listo, buscando MapRenderer...");
    loadMapRenderer();
});

async function loadMapRenderer() {
    try {
        // En Odoo 18, el módulo puede estar disponible de forma diferente
        console.log("Intentando cargar MapRenderer en Odoo 18...");
        
        // Método 1: Importación dinámica con la nueva sintaxis
        const mapRenderer = await import("@web_map/map_view/map_renderer").catch(err => {
            console.log("Método 1 falló:", err.message);
            return null;
        });
        
        if (mapRenderer && mapRenderer.MapRenderer) {
            console.log("✅ MapRenderer encontrado via importación dinámica");
            applyMapRendererPatch(mapRenderer.MapRenderer);
            return;
        }
        
        // Método 2: Usar el nuevo sistema de registro de Odoo 18
        const { registry } = await import("@web/core/registry");
        const moduleRegistry = registry.category("modules");
        
        if (moduleRegistry.contains("@web_map/map_view/map_renderer")) {
            console.log("Módulo encontrado en registry");
            const module = moduleRegistry.get("@web_map/map_view/map_renderer");
            if (module.MapRenderer) {
                applyMapRendererPatch(module.MapRenderer);
                return;
            }
        }
        
        // Método 3: Polling más agresivo para Odoo 18
        console.log("Usando polling para Odoo 18...");
        pollForMapRendererOdoo18();
        
    } catch (error) {
        console.error("Error cargando MapRenderer:", error);
        pollForMapRendererOdoo18();
    }
}

function pollForMapRendererOdoo18() {
    let attempts = 0;
    const maxAttempts = 20; // Más intentos para Odoo 18
    
    const poll = async () => {
        attempts++;
        console.log(`Intento ${attempts}/${maxAttempts} - Buscando MapRenderer en Odoo 18...`);
        
        try {
            // Verificar en diferentes ubicaciones para Odoo 18
            
            // 1. En el objeto global de Odoo
            if (window.odoo && window.odoo.define) {
                const modules = window.odoo.define._modules || {};
                const mapModule = modules['@web_map/map_view/map_renderer'];
                if (mapModule && mapModule.MapRenderer) {
                    console.log("✅ Encontrado en odoo.define._modules");
                    applyMapRendererPatch(mapModule.MapRenderer);
                    return;
                }
            }
            
            // 2. En el module loader de Odoo 18
            if (window.odoo && window.odoo.loader) {
                const loader = window.odoo.loader;
                if (loader.modules) {
                    const mapModule = loader.modules['@web_map/map_view/map_renderer'];
                    if (mapModule && mapModule.MapRenderer) {
                        console.log("✅ Encontrado en loader.modules");
                        applyMapRendererPatch(mapModule.MapRenderer);
                        return;
                    }
                }
            }
            
            // 3. Intentar importación directa de nuevo
            try {
                const { MapRenderer } = await import("@web_map/map_view/map_renderer");
                if (MapRenderer) {
                    console.log("✅ Importación directa exitosa en intento", attempts);
                    applyMapRendererPatch(MapRenderer);
                    return;
                }
            } catch (e) {
                // Ignorar error de importación
            }
            
            // 4. Buscar en el DOM elementos del mapa para verificar si está cargado
            const mapElements = document.querySelectorAll('.o_map_view, .leaflet-container');
            if (mapElements.length > 0) {
                console.log("Elementos de mapa encontrados en DOM, el módulo debería estar cargado");
            }
            
        } catch (error) {
            console.log(`Error en intento ${attempts}:`, error.message);
        }
        
        if (attempts < maxAttempts) {
            setTimeout(poll, 1500); // Más tiempo entre intentos
        } else {
            console.error("❌ MapRenderer no encontrado después de todos los intentos");
            console.log("Implementando solución alternativa para Odoo 18...");
            implementAlternativeForOdoo18();
        }
    };
    
    poll();
}

function applyMapRendererPatch(MapRenderer) {
    console.log("🎉 Aplicando patch a MapRenderer en Odoo 18...");
    
    try {
        patch(MapRenderer.prototype, {
            setup() {
                super.setup();
                console.log("MapRenderer setup ejecutado en Odoo 18");
                this.orm = useService("orm");
                this.action = useService("action");
                this.notification = useService("notification");
            },

            createMarkerPopup(markerInfo, latLongOffset = 0) {
                console.log("createMarkerPopup llamado:", markerInfo);
                const popup = super.createMarkerPopup(markerInfo, latLongOffset);
                
                // En Odoo 18 puede haber cambios en la estructura del popup
                const popupContentElement = popup.getElement ? popup.getElement() : popup._container;
                
                if (popupContentElement) {
                    // Buscar contenedor de botones con diferentes selectores para Odoo 18
                    let popupButtonsContainer = popupContentElement.querySelector(".o-map-renderer--popup-buttons") ||
                                               popupContentElement.querySelector(".leaflet-popup-content") ||
                                               popupContentElement.querySelector(".popup-buttons");
                    
                    if (!popupButtonsContainer) {
                        // Crear contenedor si no existe
                        popupButtonsContainer = document.createElement("div");
                        popupButtonsContainer.className = "o-map-renderer--popup-buttons mt-2";
                        popupContentElement.appendChild(popupButtonsContainer);
                    }
                    
                    // Verificar que no existe ya el botón
                    if (!popupButtonsContainer.querySelector(".geo-checkin-button")) {
                        const myButton = document.createElement("button");
                        myButton.className = "btn btn-primary geo-checkin-button ms-2";
                        myButton.textContent = _t("Checkin");
                        myButton.addEventListener("click", (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            this.onMyButtonClick(markerInfo);
                        });
                        popupButtonsContainer.appendChild(myButton);
                        console.log("✅ Botón Checkin agregado al popup");
                    }
                } else {
                    console.warn("No se pudo acceder al contenido del popup");
                }
                
                return popup;
            },

            async onMyButtonClick(markerInfo) {
                console.log("🎯 Checkin clicado en Odoo 18!");
                console.log("Información del registro:", markerInfo.record);
                
                if (!markerInfo.record || !markerInfo.record.id) {
                    this.notification.add(_t("No se pudo obtener la información de la tarea."), {
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
                        this.notification.add(result.message || _t("Check-in iniciado exitosamente."), {
                            type: "success",
                            sticky: false,
                        });
                    }
                } catch (error) {
                    console.error("Error en get_location_button:", error);
                    this.notification.add(error.message || _t("Error al realizar el check-in."), {
                        type: "danger",
                        sticky: true,
                    });
                }
            },
        });
        
        console.log("✅ Patch aplicado exitosamente en Odoo 18");
        
    } catch (error) {
        console.error("Error aplicando patch:", error);
        implementAlternativeForOdoo18();
    }
}

// Solución alternativa específica para Odoo 18
function implementAlternativeForOdoo18() {
    console.log("🔄 Implementando solución alternativa para Odoo 18...");
    
    // Observer más específico para Odoo 18
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    // Buscar popups de leaflet en Odoo 18
                    const popups = node.querySelectorAll('.leaflet-popup-content, .o-map-renderer--popup-content');
                    popups.forEach(popup => {
                        if (!popup.querySelector('.geo-checkin-fallback')) {
                            addCheckinButtonToPopup(popup);
                        }
                    });
                    
                    // También buscar en el nodo mismo
                    if (node.classList && (
                        node.classList.contains('leaflet-popup-content') ||
                        node.classList.contains('o-map-renderer--popup-content')
                    )) {
                        if (!node.querySelector('.geo-checkin-fallback')) {
                            addCheckinButtonToPopup(node);
                        }
                    }
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log("👀 Observer activado para Odoo 18");
}

function addCheckinButtonToPopup(popup) {
    try {
        const button = document.createElement('button');
        button.className = 'btn btn-primary geo-checkin-fallback mt-2';
        button.textContent = _t('Geo Checkin');
        button.onclick = async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            console.log("Botón fallback clickeado");
            
            // Intentar obtener información del registro desde el popup
            const recordInfo = extractRecordInfoFromPopup(popup);
            if (recordInfo && recordInfo.id) {
                try {
                    // Llamar directamente usando fetch si no tenemos ORM
                    const response = await fetch('/web/dataset/call_kw', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            jsonrpc: "2.0",
                            method: "call",
                            params: {
                                model: 'project.task',
                                method: 'get_location_button',
                                args: [recordInfo.id],
                                kwargs: {}
                            }
                        })
                    });
                    
                    const result = await response.json();
                    console.log("Resultado del check-in:", result);
                    
                } catch (error) {
                    console.error("Error en checkin fallback:", error);
                }
            }
        };
        
        popup.appendChild(button);
        console.log("✅ Botón fallback agregado");
        
    } catch (error) {
        console.error("Error agregando botón fallback:", error);
    }
}

function extractRecordInfoFromPopup(popup) {
    // Intentar extraer información del registro desde el contenido del popup
    try {
        const content = popup.textContent || popup.innerText || '';
        // Buscar patrones que puedan indicar un ID de registro
        const idMatch = content.match(/ID[:\s]*(\d+)/i) || content.match(/Task[:\s]*(\d+)/i);
        
        if (idMatch) {
            return { id: parseInt(idMatch[1]) };
        }
        
        // También buscar en atributos data-*
        const dataId = popup.getAttribute('data-record-id') || 
                      popup.querySelector('[data-record-id]')?.getAttribute('data-record-id');
        
        if (dataId) {
            return { id: parseInt(dataId) };
        }
        
    } catch (error) {
        console.error("Error extrayendo info del registro:", error);
    }
    
    return null;
}