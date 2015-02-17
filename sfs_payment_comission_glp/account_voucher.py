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

from datetime import datetime

class account_voucher(osv.osv):
    _inherit = 'account.voucher'
    
    def proforma_voucher(self, cr, uid, ids, context=None):
        invoice_pool = self.pool.get('account.invoice')
        move_line_pool = self.pool.get('account.move.line')
        user_transaction_history_pool = self.pool.get('user.transaction.history')
        res = super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)
        for voucher_obj in self.browse(cr, uid, ids, context=context):
            if voucher_obj.type == 'receipt':
                move_lines = voucher_obj.move_id and voucher_obj.move_id.line_id or []
                for move_line in move_lines:
                    reconcile_id = move_line.reconcile_id and move_line.reconcile_id.id or \
                                        move_line.reconcile_partial_id and move_line.reconcile_partial_id.id or False
                    if reconcile_id:
                        move_line_ids = move_line_pool.search(cr, uid, ['|', ('reconcile_id', '=', reconcile_id),
                                                                        ('reconcile_partial_id', '=', reconcile_id)],
                                                              context=context)
                        move_line_obj_list = move_line_pool.browse(cr, uid, move_line_ids, context=context)
                        move_ids = [x.move_id.id for x in move_line_obj_list if x.move_id]
                        invoice_ids = invoice_pool.search(cr, uid, [('move_id', 'in', move_ids)], context=context)
                        if invoice_ids:
                            amount = move_line.credit or move_line.debit or 0.00
                            type = move_line.credit and 'payment' or move_line.debit and 'refund' or 'payment'
                            invoice_id = invoice_ids[0]
                            if type == 'refund':
                                invoice_obj = invoice_pool.browse(cr, uid, invoice_id, context=context)
                                invoice_id = invoice_obj and invoice_obj.refund_invoice_id and \
                                                invoice_obj.refund_invoice_id.id or invoice_obj.id
                            vals = {
                                    'user_id': uid,
                                    'transaction_type': type,
                                    'transaction_date': datetime.now(),
                                    'payment_id': voucher_obj.id,
                                    'invoice_id': invoice_id,
                                    'amount': amount,
                                    'move_line_id': move_line.id
                                    }
                            history_id = user_transaction_history_pool.create(cr, uid, vals, context=context)
        return res
    
    def cancel_voucher(self, cr, uid, ids, context=None):
        user_tran_history_pool = self.pool.get('user.transaction.history')
        res = super(account_voucher, self).cancel_voucher(cr, uid, ids, context=context)
        user_tran_history_ids = user_tran_history_pool.search(cr, uid, [('payment_id', 'in', ids)],
                                                              context=context)
        user_tran_history_pool.unlink(cr, uid, user_tran_history_ids, context=context)
        return res
    
account_voucher()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
