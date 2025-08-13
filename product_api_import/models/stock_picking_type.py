from odoo import models, fields, api

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_api_import = fields.Boolean(
        string='Importado por API',
        default=False,
        help='Indica si este tipo de operación fue importado desde la API externa'
    )

    def button_import_from_api(self):
        """Método llamado por el botón en la vista árbol"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importar Productos desde API',
            'res_model': 'product.api.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_type_id': self.id},
        }