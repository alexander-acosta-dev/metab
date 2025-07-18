# -*- coding: utf-8 -*-
import requests
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)

ACCESS_TOKEN = 'EAANetaXL71wBPLQt1ZCiPWCM0SSF64qiYYaSAb4KE0sElV9tKDZAbN34PUZBJ7pSGxZAmrG8LZBZBNqIxTICjJFpU5HAqvQ4YBnXq8dugUFipZCMZCZC7hZCgRVIUtKMXuqDSB1IwiO6UOjpEDvwZBBWckJY6gLKLynMvCihxKUZBTn4mX4ffpR6boO80SZA6PxICnhMZAUDZB3DlgfVQ3DNZCFbhgZDZD'
FORM_ID = '123456789012345'

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def import_meta_leads(self):
        """Importa leads desde Meta Business, los coloca en la etapa 'Nuevo' y les asigna la etiqueta 'Meta'."""
        url = f'https://graph.facebook.com/v19.0/{FORM_ID}/leads'
        params = {'access_token': ACCESS_TOKEN}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data:
                return {'status': 'error', 'message': _('No se encontraron leads.')}

            # Etapa inicial
            stage = self.env['crm.stage'].search([], order="sequence asc", limit=1)

            # Etiqueta Meta (crear si no existe)
            tag = self.env['crm.tag'].search([('name', '=', 'Meta')], limit=1)
            if not tag:
                tag = self.env['crm.tag'].create({'name': 'Meta'})

            count = 0
            for lead in data['data']:
                field_data = {item['name']: item['values'][0] for item in lead.get('field_data', [])}

                first_name = field_data.get('first_name', '')
                last_name = field_data.get('last_name', '')
                email = field_data.get('email')
                phone = field_data.get('phone_number')
                city = field_data.get('city')
                state = field_data.get('state')
                zip_code = field_data.get('zip_code')
                country_name = field_data.get('country')

                name = (first_name + ' ' + last_name).strip() or 'Meta Lead'

                # País
                country_id = None
                if country_name:
                    country = self.env['res.country'].search([('name', 'ilike', country_name)], limit=1)
                    if country:
                        country_id = country.id

                # Evita duplicados simples
                existing = self.env['crm.lead'].search([('email_from', '=', email)], limit=1)
                if existing:
                    continue

                self.create({
                    'name': name,
                    'email_from': email,
                    'phone': phone,
                    'stage_id': stage.id,
                    'tag_ids': [(6, 0, [tag.id])],  # 👈 Etiqueta Meta
                    'city': city,
                    'zip': zip_code,
                    'state_id': self.env['res.country.state'].search([
                        ('name', 'ilike', state),
                        ('country_id', '=', country_id)
                    ], limit=1).id if state and country_id else False,
                    'country_id': country_id,
                    'description': f"Importado desde Meta Lead ID: {lead['id']}",
                })
                count += 1

            return {'status': 'ok', 'message': _(f'{count} leads importados correctamente.')}

        except Exception as e:
            _logger.exception("Error al importar leads desde Meta:")
            return {'status': 'error', 'message': str(e)}
