from odoo import models, fields, api
import urllib.parse

class GoogleCalendarService(models.Model):
    _name = 'google.calendar.service'
    _description = 'Servicio para sincronización con Google Calendar'

    user_id = fields.Many2one('res.users', string="Usuario", required=True)
    access_token = fields.Char(string="Access Token")
    refresh_token = fields.Char(string="Refresh Token")
    token_expiry = fields.Datetime(string="Token Expiración")

    def get_auth_url(self):
        client_id = self.env['ir.config_parameter'].sudo().get_param('google_calendar.client_id')
        redirect_uri = self.env['ir.config_parameter'].sudo().get_param('google_calendar.redirect_uri')
        scope = 'https://www.googleapis.com/auth/calendar'
        state = str(self.user_id.id)  # Para identificar el usuario en el callback

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': scope,
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state,
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)