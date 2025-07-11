# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class usuarios_portal(models.Model):
#     _name = 'usuarios_portal.usuarios_portal'
#     _description = 'usuarios_portal.usuarios_portal'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

