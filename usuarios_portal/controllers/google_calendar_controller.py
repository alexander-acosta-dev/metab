from odoo import http
from odoo.http import request

class GoogleCalendarSyncController(http.Controller):

    @http.route('/google_calendar/form', type='http', auth='user', website=True)
    def google_calendar_form(self, **kwargs):
        # Renderiza una plantilla q contiene el formulario para sincronizar
        return request.render('usuarios_portal.google_calendar_form_template')

    @http.route('/google_calendar/sync', type='http', auth='user', website=True)
    def sync_google_calendar(self, **kwargs):
        service = request.env['google.calendar.service'].sudo()
        redirect_url = service.get_auth_url()
        return request.redirect(redirect_url)