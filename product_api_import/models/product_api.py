from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductAPI(models.Model):
    _name = 'product.api.import'
    _description = 'Importación de Productos desde API'

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Tipo de Operación',
        required=True  # Ahora el requerido se maneja en el modelo
    )

    @api.constrains('picking_type_id')
    def _check_picking_type(self):
        """Validación adicional si es necesaria"""
        for record in self:
            if not record.picking_type_id:
                raise ValidationError(_("Debe seleccionar un tipo de operación"))

    def button_import_products(self):
        """Método principal de importación"""
        self.ensure_one()
        try:
            if not self.picking_type_id:
                raise UserError(_("Debe seleccionar un tipo de operación primero"))
                
            # Resto del código de importación...