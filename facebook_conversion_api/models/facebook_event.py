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

    def send_event(self, event_name, email, phone, country, city, region, ip_address, user_agent, external_id, currency="CLP", value=0.0):

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
            "client_ip_address": ip_address,
            "client_user_agent": user_agent,
        }

        if email:
            user_data["em"] = self.hash_data(email)
        if phone:
            user_data["ph"] = self.hash_data(phone)
        if country and len(country.strip()) == 2:
            user_data["country"] = self.hash_data(country.strip().lower())
        if city:
            user_data["ct"] = self.hash_data(city.strip().lower())
        if region:
            user_data["st"] = self.hash_data(region.strip().lower())
        if external_id:
            user_data["external_id"] = self.hash_data(external_id)

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

        _logger.debug(f"Payload enviado a Meta: {json.dumps(payload, indent=2)}")
        
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
    meta_sent_date = fields.Datetime(string="Fecha de Envío a Meta", readonly=True)

    def action_send_facebook_event(self):
        for lead in self:
            if not lead.email_from and not lead.phone:
                raise UserError("Meta requiere al menos email o teléfono válidos para enviar el evento.")

            country = lead.country_id.code if lead.country_id else None
            city = lead.city if lead.city else None
            region = lead.state_id.name if lead.state_id else None

            # Verificar si ya fue enviado y si fue modificado después del último envío
            if lead.meta_sent_date and lead.write_date <= lead.meta_sent_date:
                continue  # Ya enviado y sin cambios desde entonces

            status_code, response_text, event_id = self.env['facebook.conversion.api'].send_event(
                event_name="Lead",
                email=lead.email_from,
                phone=lead.phone,
                country=country,
                city=city,
                region=region,
                ip_address=self._context.get('client_ip', '127.0.0.1'),
                user_agent=self._context.get('user_agent', 'Odoo'),
                external_id=str(lead.id),
                value=0
            )

            if status_code == 200:
                # Guardar en el campo
                lead.event_facebook_id = event_id
                lead.meta_sent_date = fields.Datetime.now()

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

