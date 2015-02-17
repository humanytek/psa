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

import openerp.addons.decimal_precision as dp

class user_transaction_history(osv.osv):
    _name = 'user.transaction.history'
    _description = 'Model to keep record of user payments and refund'
    _rec_name = 'transaction_date'
    _columns = {
                'user_id': fields.many2one('res.users', 'User'),
                'transaction_date': fields.related('payment_id', 'date', type="date", string="Transaction Date",
                                                   store=True),
#                 'transaction_date': fields.date('Transaction Date'),
                'transaction_type': fields.selection([('payment', 'Payment'), ('refund', 'Refund')],
                                                     'Transaction Type'),
                'invoice_id': fields.many2one('account.invoice', 'Related Invoice'),
                'payment_id': fields.many2one('account.voucher', 'Related Payment'),
                'move_line_id': fields.many2one('account.move.line', 'Related Journal Item'),
                'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'))
                }
user_transaction_history()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
