odoo.define('product_api_import.PickingTypeList', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var core = require('web.core');
    var _t = core._t;

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.modelName === 'stock.picking.type') {
                // Asegurar que el botón se posicione correctamente
                var $searchView = this.$('.o_searchview');
                if ($searchView.length) {
                    var $button = this.$buttons.find('button[name="button_import_from_api"]');
                    $button.addClass('ml-2').insertAfter($searchView);
                }
            }
        }
    });
});