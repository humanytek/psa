# -*- encoding: utf-8 -*-
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


class collect_report_wizard(osv.osv_memory):
    _name = 'collect.report.wizard'
    
    _columns = {
                'start_date': fields.date("Initial date"),
                'end_date': fields.date("Final date"),
                'user_id': fields.many2one('res.users', 'User'),
                'currency_id': fields.many2one('res.currency', 'Currency')
                }
    
    def view_collect_report(self, cr, uid, ids, context):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids[0], context=context)
        invoice_pool = self.pool.get('account.invoice')
        search_string = [('date_invoice', '>=', data['start_date']),('date_invoice', '<=',data['end_date']),('state', '=','paid'),
                         ('currency_id', '=', data['currency_id'][0]),('create_uid', '=', data['user_id'][0])]
        invoice_ids = invoice_pool.search(cr, uid,search_string,order='date_invoice',context=context)
        context['start_date'] = data['start_date']
        context['user_id'] = data['user_id']
        context['end_date'] = data['end_date']
        context['currency_id'] = data['currency_id']
        context['active_ids'] = invoice_ids
        if data['start_date'] > data['end_date']:
            raise osv.except_osv(_('Warning!'), _('Initial date  must be lesser than the Final date'))
        if not  invoice_ids:
            raise osv.except_osv(_('Warning!'), _('No such invoices for corresponding date'))
        
        datas = {
             'ids': invoice_ids,
             'model': 'collect.report.wizard',
             'form': data
                 }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'collect_report',
            'datas': datas,
            'context': context
            }
        
    
collect_report_wizard()

##############################################################################