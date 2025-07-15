import requests
import json
import hashlib
import uuid
import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class FacebookConversionAPI(models.Model):
    _name = 'facebook.conversion.api'
    _description = 'Facebook Conversion API Integration'

    def hash_data(self, data):
        if data:
            return hashlib.sha256(data.strip().lower().encode()).hexdigest()
        return None

    def send_event(self, event_name, email, phone, ip_address, user_agent, currency="CLP", value=0.0):
        token = 'EAAP3lDfOoDEBPPa6iVkz9IIAcl16buaOiGgTRawUN20lYI5AjmkLWHSZAQDMvmMOI2IeRPawyXOUYEk8nsP4ZCPoWPeM6QqcGLklzTIBz1JYYJYhfXfJGPoeMfpCeCNRbtIQd17OKV73ssE91uIvg1sg2v904p7by3O6cQW3IEIZB2kbY2pPMy6ZAfjfcgZDZD'
        pixel_id = '943376917913790'

        url = f'https://graph.facebook.com/v23.0/{pixel_id}/events'
        event_id = str(uuid.uuid4())

        user_data = {
            "em": self.hash_data(email),
            "ph": self.hash_data(phone),
            "client_ip_address": ip_address,
            "client_user_agent": user_agent,
        }

        custom_data = {
            "currency": currency,
            "value": value
        }

        payload = {
            "data": [{
                "event_name": event_name,
                "event_time": int(fields.datetime.now().timestamp()),
                "event_id": event_id,
                "user_data": user_data,
                "custom_data": custom_data,
                "action_source": "website"
            }],
            "access_token": token
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            _logger.info(f"Evento '{event_name}' enviado correctamente a Meta. Event ID: {event_id}")
            return response.status_code, response.text, event_id
        else:
            raise Exception(f'Error {response.status_code}: {response.text}')


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    event_facebook_id = fields.Char(string="ID Evento Meta", readonly=True)

    def action_send_facebook_event(self):
        for lead in self:
            if not lead.email_from:
                raise UserError("La oportunidad no tiene correo.")
            if not lead.phone:
                raise UserError("La oportunidad no tiene número de teléfono.")

            status_code, response_text, event_id = self.env['facebook.conversion.api'].send_event(
                event_name="Lead",
                email=lead.email_from,
                phone=lead.phone,
                ip_address=self._context.get('client_ip', '127.0.0.1'),
                user_agent=self._context.get('user_agent', 'Odoo'),
                value=0
            )

            if status_code == 200:
                # Guardar en el campo
                lead.event_facebook_id = event_id

                # 📝 Registrar nota en chatter
                lead.message_post(
                    body="✅ Evento enviado a Meta Conversion API correctamente.",
                    subtype_xmlid="mail.mt_note"
                )

                # 🏷️ Agregar etiqueta
                tag = self.env['crm.tag'].search([('name', '=', 'Enviado a Meta')], limit=1)
                if not tag:
                    tag = self.env['crm.tag'].create({'name': 'Enviado a Meta'})
                lead.tag_ids = [(4, tag.id)]

            else:
                raise UserError(f'Error al enviar evento a Meta: {response_text}')

