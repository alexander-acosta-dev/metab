odoo.define('product_api_import.PickingTypeList', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var core = require('web.core');
    var _t = core._t;

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.modelName === 'stock.picking.type') {
                // Mover el botón al lado de la búsqueda
                var $button = this.$buttons.find('button[name="button_import_from_api"]');
                $button.detach().insertAfter(this.$('.o_searchview'));
                $button.addClass('ml-2');
            }
        }
    });
});