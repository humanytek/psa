# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 SF Soluciones.
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

from osv import osv, fields

from tools.translate import _

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
                'production_lot_id': fields.many2one('stock.production.lot', 'Serial Number')
                }
    
account_invoice_line()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    
    def invoice_validate(self, cr, uid, ids, context=None):
        for invoice_obj in self.browse(cr, uid, ids, context=context):
            for line in invoice_obj.invoice_line:
                if not line.production_lot_id and line.product_id:
                    if line.product_id.track_production or line.product_id.track_incoming or \
                                        line.product_id.track_outgoing:
                        raise osv.except_osv(_('Error!'),
                                             _('You are triyng to invoice products which has serial number control'))
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        return res
    
account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
