from odoo import http, fields
from odoo.http import request

class GeoCheckInController(http.Controller):

    @http.route('/checkin/manual', type='json', auth="user", methods=['POST'], csrf=False)
    def check_in(self):
        # Validación de conexión sospechosa
        if request.session.get('vpn_detectado') or request.session.get('timezone_mismatch'):
            return {
                'error': 'Conexión sospechosa detectada. No se permite el check-in desde VPN, proxy, datacenter o zona horaria incorrecta.'
            }

        user = request.env.user

        checkin = request.env['hr.attendance'].sudo().create({
            'employee_id': user.employee_id.id,
            'check_in': fields.Datetime.now(),
        })

        return {
            'checkin_id': checkin.id,
            'check_in': checkin.check_in,
        }