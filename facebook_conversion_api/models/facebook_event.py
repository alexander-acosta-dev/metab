import requests
import json
import hashlib
import uuid
import time
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

        pixel_id = self.env['ir.config_parameter'].sudo().get_param('meta.pixel_id')
        token = self.env['ir.config_parameter'].sudo().get_param('meta.access_token')

        if not pixel_id or not token:
            raise UserError("Configura Pixel ID y Access Token de Meta en Parámetros del sistema.")

        url = f'https://graph.facebook.com/v23.0/{pixel_id}/events'

        event_id = str(uuid.uuid4())

        headers = {
            'Content-Type': 'application/json'
        }

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
                "event_time": int(time.time()),
                "event_id": event_id,
                "user_data": user_data,
                "custom_data": custom_data,
                "action_source": "system_generated"
            }],
            "access_token": token
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error enviando evento a Meta: {e}")
            raise UserError(f"Error enviando evento a Meta: {e}")

        _logger.info(f"Evento '{event_name}' enviado correctamente a Meta. Event ID: {event_id}")
        return response.status_code, response.text, event_id


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    event_facebook_id = fields.Char(string="ID Evento Meta", readonly=True)

    def action_send_facebook_event(self):
        for lead in self:
            if not lead.email_from:
                raise UserError("La oportunidad no tiene correo.")
            if not lead.phone:
                raise UserError("La oportunidad no tiene número de teléfono.")

            if lead.event_facebook_id:
                # Ya enviado antes, evitar duplicados o enviar con lógica distinta
                continue

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

