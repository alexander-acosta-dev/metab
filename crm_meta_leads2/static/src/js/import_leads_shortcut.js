/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";
import { Component } from "@odoo/owl";

// IMPORTAMOS el template aunque no lo usemos visualmente
import { xml } from "@odoo/owl";

export class MetaLeadImportShortcut extends Component {
    static template = "crm_meta_leads.MetaLeadImportShortcut";

    setup() {
        this.rpc = useService("rpc");

        onMounted(() => {
            document.addEventListener("keydown", this.onKeyDown);
        });
    }

    onKeyDown = (e) => {
        if (e.ctrlKey && !e.altKey && !e.metaKey) {
            this.rpc
                .query({
                    model: "crm.lead",
                    method: "import_meta_leads",
                    args: [],
                })
                .then((result) => {
                    this.showNotification("Leads importados desde Meta");
                })
                .catch((err) => {
                    console.error("Error al importar leads:", err);
                    this.showNotification("Error al importar leads", true);
                });
        }
    };

    showNotification(message, isWarning = false) {
        this.env.services.notification.add(message, {
            type: isWarning ? "danger" : "success",
        });
    }
}

registry.category("main_components").add("meta_lead_import_shortcut", {
    Component: MetaLeadImportShortcut,
    props: {},
});
