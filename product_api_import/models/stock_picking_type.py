from odoo import models, fields, api, _

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def button_import_from_api(self):
        """Acción para el botón de importación"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importar Productos',
            'res_model': 'product.api.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_type_id': self.id},
        }