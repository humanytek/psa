# -*- encoding: utf-8 -*
##############################################################################
#
#    Copyright (c) 2013 SF Soluciones.
#    (http://www.sfsoluciones.com)
#    contacto@sfsoluciones.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv
from openerp.tools.translate import _

class cash_report_wizard(osv.osv_memory):
    _name = 'cash.report.wizard'
    
    _columns = {
                'start_date': fields.date("Initial date"),
                'end_date': fields.date("Final date"),
                'user_id': fields.many2one('res.users', 'User')
                }
    
    def view_cash_report(self, cr, uid, ids, context):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids[0], context=context)
        voucher_pool = self.pool.get('account.voucher')
        search_string = [('date', '>=', data['start_date']),('date', '<=',data['end_date']),('state', '=','posted'),('create_uid', '=', data['user_id'][0])]
        voucher_ids = voucher_pool.search(cr, uid,search_string,order='date',context=context)
        context['start_date'] = data['start_date']
        context['user_id'] = data['user_id'][1]
        context['end_date'] = data['end_date']
        context['active_ids'] = voucher_ids
        if data['start_date'] > data['end_date']:
            raise osv.except_osv(_('Warning!'), _('Initial date  must be lesser than the Final date'))
        if not  voucher_ids:
            raise osv.except_osv(_('Warning!'), _('No such invoices for corresponding date'))
        
        datas = {
             'ids': voucher_ids,
             'model': 'cash.report.wizard',
             'form': data
                 }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'cash_report',
            'datas': datas,
            'context': context
            }
        
    
cash_report_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:-