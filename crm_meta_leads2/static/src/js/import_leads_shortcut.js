odoo.define('crm_meta_leads.import_shortcut', function (require) {
    "use strict";

    const publicWidget = require('web.public.widget');
    const rpc = require('web.rpc');

    publicWidget.Widget.extend({
        selector: 'body',
        start: function () {
            this._super.apply(this, arguments);
            document.addEventListener('keydown', function (e) {
                if (e.ctrlKey && !e.altKey && !e.metaKey) {
                    rpc.query({
                        model: 'crm.lead',
                        method: 'import_meta_leads',
                        args: [],
                    }).then(function (result) {
                        alert(result.message);
                    }).catch(function (err) {
                        console.error("Error al importar leads:", err);
                        alert("Error al importar leads.");
                    });
                }
            });
        }
    });
});
