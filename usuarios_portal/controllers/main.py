from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class MyPortalLeads(CustomerPortal):
    _items_per_page = 20

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        
        if 'leads_count' in counters:
            # Buscar leads donde el usuario es el responsable O donde está relacionado como cliente
            domain = [
                '|', 
                ('user_id', '=', user.id),
                ('partner_id', '=', user.partner_id.id)
            ]
            leads_count = request.env['crm.lead'].sudo().search_count(domain)
            values['leads_count'] = leads_count
            
        if 'meetings_count' in counters:
            domain = [('partner_ids', 'in', user.partner_id.id)]
            meetings_count = request.env['calendar.event'].sudo().search_count(domain)
            values['meetings_count'] = meetings_count
            
        return values

    @http.route(['/my/leads', '/my/leads/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leads(self, page=1, **kw):
        try:
            user = request.env.user
            # Dominio más amplio para incluir leads donde el usuario es responsable o cliente
            domain = [
                '|', 
                ('user_id', '=', user.id),
                ('partner_id', '=', user.partner_id.id)
            ]
            
            leads_sudo = request.env['crm.lead'].sudo().search(domain)
            total = len(leads_sudo)
            
            pager = portal_pager(
                url="/my/leads", 
                total=total, 
                page=page, 
                step=self._items_per_page
            )
            
            offset = pager.get('offset', 0)
            leads = leads_sudo[offset: offset + self._items_per_page]
            
            return request.render("usuarios_portal.portal_my_leads", {
                'leads': leads,
                'pager': pager,
                'page_name': 'leads',
                'user': user,
                'default_url': '/my/leads',
            })
        except Exception as e:
            _logger.exception("Error rendering leads view: %s", e)
            return request.render("portal.portal_error", {
                'error_message': 'Error al cargar las oportunidades. Contacte al administrador.'
            })

    @http.route(['/my/leads/detail/<int:lead_id>'], type='http', auth="user", website=True)
    def portal_my_lead_detail(self, lead_id, **kw):
        try:
            user = request.env.user
            lead = request.env['crm.lead'].sudo().browse(lead_id)
            
            # Verificar acceso: usuario responsable o cliente
            if not lead.exists() or (lead.user_id.id != user.id and lead.partner_id.id != user.partner_id.id):
                return request.redirect('/my/leads')
            
            return request.render("usuarios_portal.portal_my_lead_detail", {
                'lead': lead,
                'page_name': 'lead_detail',
                'user': user,
            })
        except Exception as e:
            _logger.exception("Error rendering lead detail: %s", e)
            return request.redirect('/my/leads')

    @http.route(['/my/leads/create', '/my/leads/edit/<int:lead_id>'], type='http', auth="user", website=True)
    def portal_my_lead_form(self, lead_id=None, **kw):
        try:
            user = request.env.user
            Lead = request.env['crm.lead'].sudo()
            
            if lead_id:
                lead = Lead.browse(lead_id)
                if not lead.exists() or (lead.user_id.id != user.id and lead.partner_id.id != user.partner_id.id):
                    return request.redirect('/my/leads')
            else:
                lead = Lead

            stages = request.env['crm.stage'].sudo().search([])
            
            return request.render("usuarios_portal.portal_my_lead_form", {
                'lead': lead if lead_id else False,
                'stages': stages,
                'error': {},
                'warning': {},
                'page_name': 'lead_form',
                'user': user,
            })
        except Exception as e:
            _logger.exception("Error rendering lead form: %s", e)
            return request.redirect('/my/leads')

    @http.route(['/my/leads/save', '/my/leads/save/<int:lead_id>'], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_lead_save(self, lead_id=None, **post):
        try:
            user = request.env.user
            Lead = request.env['crm.lead'].sudo()
            error = {}
            
            # Validaciones
            name = post.get('name', '').strip()
            if not name:
                error['name'] = 'El nombre es obligatorio.'
            
            try:
                revenue = float(post.get('expected_revenue', 0) or 0)
            except ValueError:
                revenue = 0.0
                error['expected_revenue'] = 'Ingrese un valor numérico válido.'

            stage_id = False
            if post.get('stage_id'):
                try:
                    stage_id = int(post.get('stage_id'))
                except ValueError:
                    error['stage_id'] = 'Etapa inválida.'

            if error:
                lead = Lead.browse(lead_id) if lead_id else False
                stages = request.env['crm.stage'].sudo().search([])
                return request.render("usuarios_portal.portal_my_lead_form", {
                    'lead': lead,
                    'stages': stages,
                    'error': error,
                    'warning': {'general': "Corrige los errores."},
                    'post': post,
                    'page_name': 'lead_form',
                    'user': user,
                })

            vals = {
                'name': name,
                'expected_revenue': revenue,
                'stage_id': stage_id,
            }

            if lead_id:
                # Editar lead existente
                lead = Lead.browse(lead_id)
                if lead.exists() and (lead.user_id.id == user.id or lead.partner_id.id == user.partner_id.id):
                    lead.write(vals)
            else:
                # Crear nuevo lead
                vals.update({
                    'user_id': user.id,
                    'partner_id': user.partner_id.id,
                    'type': 'opportunity',
                })
                Lead.create(vals)
            
            return request.redirect('/my/leads')
        except Exception as e:
            _logger.exception("Error saving lead: %s", e)
            return request.redirect('/my/leads')

    @http.route(['/my/leads/delete/<int:lead_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_lead_delete(self, lead_id, **kw):
        try:
            user = request.env.user
            lead = request.env['crm.lead'].sudo().browse(lead_id)
            
            if lead.exists() and (lead.user_id.id == user.id or lead.partner_id.id == user.partner_id.id):
                lead.unlink()
        except Exception as e:
            _logger.exception("Error deleting lead: %s", e)
        
        return request.redirect('/my/leads')

    # ##############################
    # REUNIONES
    # ##############################

    @http.route(['/my/meetings', '/my/meetings/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_meetings(self, page=1, **kw):
        try:
            user = request.env.user
            domain = [('partner_ids', 'in', user.partner_id.id)]
            
            total = request.env['calendar.event'].sudo().search_count(domain)
            pager = portal_pager(
                url="/my/meetings", 
                total=total, 
                page=page, 
                step=self._items_per_page
            )
            
            offset = pager.get('offset', 0)
            meetings = request.env['calendar.event'].sudo().search(
                domain, 
                offset=offset, 
                limit=self._items_per_page, 
                order="start desc"
            )
            
            return request.render("usuarios_portal.portal_my_meetings", {
                'meetings': meetings,
                'pager': pager,
                'page_name': 'meetings',
                'user': user,
                'default_url': '/my/meetings',
            })
        except Exception as e:
            _logger.exception("Error rendering meetings view: %s", e)
            return request.render("portal.portal_error", {
                'error_message': 'Error al cargar las reuniones. Contacte al administrador.'
            })

    @http.route(['/my/meetings/detail/<int:meeting_id>'], type='http', auth="user", website=True)
    def portal_my_meeting_detail(self, meeting_id, **kw):
        try:
            user = request.env.user
            meeting = request.env['calendar.event'].sudo().browse(meeting_id)
            
            if not meeting.exists() or user.partner_id.id not in meeting.partner_ids.ids:
                return request.redirect('/my/meetings')
            
            return request.render("usuarios_portal.portal_my_meeting_detail", {
                'meeting': meeting,
                'page_name': 'meeting_detail',
                'user': user,
            })
        except Exception as e:
            _logger.exception("Error rendering meeting detail: %s", e)
            return request.redirect('/my/meetings')

    @http.route(['/my/meetings/create', '/my/meetings/edit/<int:meeting_id>'], type='http', auth="user", website=True)
    def portal_my_meeting_form(self, meeting_id=None, **kw):
        try:
            user = request.env.user
            Meeting = request.env['calendar.event'].sudo()
            
            if meeting_id:
                meeting = Meeting.browse(meeting_id)
                if not meeting.exists() or user.partner_id.id not in meeting.partner_ids.ids:
                    return request.redirect('/my/meetings')
            else:
                meeting = False
            
            # Obtener partners disponibles (excluir el usuario actual)
            partners = request.env['res.partner'].sudo().search([
                ('id', '!=', user.partner_id.id),
                ('is_company', '=', False)
            ])
            
            return request.render("usuarios_portal.portal_my_meeting_form", {
                'meeting': meeting,
                'partners': partners,
                'error': {},
                'warning': {},
                'page_name': 'meeting_form',
                'user': user,
            })
        except Exception as e:
            _logger.exception("Error rendering meeting form: %s", e)
            return request.redirect('/my/meetings')

    @http.route(['/my/meetings/save', '/my/meetings/save/<int:meeting_id>'], type='http', auth="user", methods=['POST'], website=True)
    def portal_my_meeting_save(self, meeting_id=None, **post):
        try:
            user = request.env.user
            Meeting = request.env['calendar.event'].sudo()
            error = {}
            
            # Validaciones
            name = post.get('name', '').strip()
            if not name:
                error['name'] = 'El asunto es obligatorio.'
            
            start_str = post.get('start_datetime', '').strip()
            start_dt = None
            if start_str:
                try:
                    start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    error['start_datetime'] = 'Fecha y hora inválida.'
            else:
                error['start_datetime'] = 'La fecha y hora son obligatorias.'
            
            try:
                duration = float(post.get('duration', 1) or 1)
            except ValueError:
                duration = 1.0
                error['duration'] = 'Duración inválida.'

            # Procesar asistentes
            partner_ids = [user.partner_id.id]  # Siempre incluir al usuario actual
            selected_partners = request.httprequest.form.getlist('partner_ids')
            for partner_id in selected_partners:
                try:
                    partner_ids.append(int(partner_id))
                except ValueError:
                    continue

            if error:
                meeting = Meeting.browse(meeting_id) if meeting_id else False
                partners = request.env['res.partner'].sudo().search([
                    ('id', '!=', user.partner_id.id),
                    ('is_company', '=', False)
                ])
                return request.render("usuarios_portal.portal_my_meeting_form", {
                    'meeting': meeting,
                    'partners': partners,
                    'error': error,
                    'warning': {'general': 'Corrige los errores.'},
                    'post': post,
                    'page_name': 'meeting_form',
                    'user': user,
                })

            vals = {
                'name': name,
                'start': start_dt,
                'duration': duration,
                'partner_ids': [(6, 0, list(set(partner_ids)))],
            }

            if meeting_id:
                # Editar reunión existente
                meeting = Meeting.browse(meeting_id)
                if meeting.exists() and user.partner_id.id in meeting.partner_ids.ids:
                    meeting.write(vals)
            else:
                # Crear nueva reunión
                Meeting.create(vals)

            return request.redirect('/my/meetings')
        except Exception as e:
            _logger.exception("Error saving meeting: %s", e)
            return request.redirect('/my/meetings')

    @http.route(['/my/meetings/delete/<int:meeting_id>'], type='http', auth="user", website=True, methods=['POST'])
    def portal_my_meeting_delete(self, meeting_id, **kw):
        try:
            user = request.env.user
            meeting = request.env['calendar.event'].sudo().browse(meeting_id)
            
            if meeting.exists() and user.partner_id.id in meeting.partner_ids.ids:
                meeting.unlink()
        except Exception as e:
            _logger.exception("Error deleting meeting: %s", e)
        
        return request.redirect('/my/meetings')
