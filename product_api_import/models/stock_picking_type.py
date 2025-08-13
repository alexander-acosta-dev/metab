from odoo import models, fields, api

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_api_import = fields.Boolean(
        string='Importado por API',
        default=False,
        help='Indica si este tipo de operación fue importado desde la API externa',
        tracking=True
    )

    @api.model
    def create(self, vals):
        """Marcar tipos de operación creados por API"""
        if self.env.context.get('from_api_import'):
            vals['is_api_import'] = True
        return super().create(vals)