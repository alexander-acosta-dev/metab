odoo.define('product_api_import.ImportButton', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var rpc = require('web.rpc');

    FormController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            var self = this;

            if (this.modelName === 'product.api.import') {
                this.$buttons.find('button[name="import_products"]').click(function() {
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
                var message;
                if (result.error) {
                    message = `<div class="alert alert-danger">
                        <strong>Error:</strong> ${result.error}
                    </div>`;
                } else {
                    message = `<div class="alert alert-success">
                        <strong>Importación completada:</strong><br>
                        Productos creados: ${result.created}<br>
                        Productos actualizados: ${result.updated}<br>
                        Total procesados: ${result.total}
                    </div>`;
                }
                
                self.$el.find('#import_results').html(message);
                self.$buttons.find('button').prop('disabled', false);
            });
        }
    });
});