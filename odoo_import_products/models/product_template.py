from odoo import models, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_open_import_wizard(self):
        return {
            'name': _('Importar Productos'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_ids': self.ids},
        }