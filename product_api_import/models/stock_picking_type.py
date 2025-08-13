from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_api_import = fields.Boolean(
        string='Importado por API',
        default=False,
        help='Indica si este tipo de operación fue importado desde la API externa'
    )