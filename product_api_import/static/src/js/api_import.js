odoo.define('product_api_import.ImportButton', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    FormController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.modelName === 'product.api.import') {
                this.$buttons.find('button[name="button_import_products"]')
                    .off('click')
                    .on('click', this._importProducts.bind(this));
            }
        },

        _importProducts: function() {
            var self = this;
            var $button = this.$buttons.find('button[name="button_import_products"]');
            
            // Mostrar spinner y deshabilitar botón
            $button.prop('disabled', true)
                   .prepend($('<i/>', {class: 'fa fa-spinner fa-spin mr-2'}));

            rpc.query({
                route: '/product_api/import',
            }).then(function(result) {
                // Restaurar botón
                $button.prop('disabled', false).find('i').remove();
                
                if (result.success) {
                    self.displayNotification({
                        title: _t("Éxito"),
                        message: result.result && result.result.params ? 
                                result.result.params.message : 
                                _t("Importación completada"),
                        type: 'success',
                        sticky: false
                    });
                    self.reload();
                } else {
                    self.displayNotification({
                        title: _t("Error"),
                        message: result.error || _t("Error desconocido"),
                        type: 'danger',
                        sticky: true
                    });
                }
            }).catch(function(error) {
                $button.prop('disabled', false).find('i').remove();
                self.displayNotification({
                    title: _t("Error"),
                    message: _t("Error en la comunicación con el servidor"),
                    type: 'danger',
                    sticky: true
                });
                console.error("API Import Error:", error);
            });
        }
    });
});