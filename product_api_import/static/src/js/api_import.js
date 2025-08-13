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
                this.$buttons.find('button[name="button_import_products"]').on('click', function() {
                    self._importProducts();
                });
            }
        },

        _importProducts: function() {
            var self = this;
            var $button = this.$buttons.find('button[name="button_import_products"]');
            $button.prop('disabled', true).prepend('<i class="fa fa-spinner fa-spin mr-2"/>');
            
            rpc.query({
                route: '/product_api/import',
            }).then(function(result) {
                $button.prop('disabled', false).find('i').remove();
                
                if (result.success) {
                    self.do_notify(
                        _t("Éxito"),
                        result.result.params.message || _t("Operación completada"),
                        true
                    );
                    self.reload();
                } else {
                    self.do_warn(
                        _t("Error"),
                        result.error || _t("Error desconocido al importar productos"),
                        true
                    );
                }
            }).catch(function(error) {
                $button.prop('disabled', false).find('i').remove();
                self.do_warn(
                    _t("Error"),
                    _t("Error en la comunicación con el servidor"),
                    true
                );
                console.error(error);
            });
        }
    });
});