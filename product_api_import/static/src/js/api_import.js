odoo.define('product_api_import.ImportButton', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    FormController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            var self = this;

            if (this.modelName === 'product.api.import') {
                this.$buttons.find('button[name="button_import_products"]').click(function() {
                    self._importProducts();
                });
            }
        },

        _importProducts: function() {
            var self = this;
            this.$buttons.find('button').prop('disabled', true);
            
            rpc.query({
                route: '/product_api/import',
            }).then(function(result) {
                self.$buttons.find('button').prop('disabled', false);
                
                if (result.success) {
                    self.do_notify(
                        _t("Éxito"),
                        _t("Importación completada correctamente"),
                        true
                    );
                } else {
                    self.do_warn(
                        _t("Error"),
                        result.error || _t("Error desconocido al importar productos")
                    );
                }
            });
        }
    });
});