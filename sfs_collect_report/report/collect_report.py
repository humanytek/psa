# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import pooler
from itertools import chain
from openerp.report import report_sxw

class collect_report_acc(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        
        super(collect_report_acc, self).__init__(cr, uid, name, context=context)
        u_name = context['user_id']
        invoice_ids = context['active_ids']
        self.localcontext.update({
            'time': time, 
#             'start_date': context['start_date'],
#             'end_date': context['end_date'],
#             'user_name': u_name,
            'invoice_ids': context['active_ids'],
            'invoice_list': self.get_invoice_obj,
            'get_debit_total': self.get_debit_total,
            'get_credit_total': self.get_credit_total,
            'get_balance_total': self.get_balance_total,
            'get_total_debit': self.get_total_debit,
            'get_total_credit': self.get_total_credit,
#             'get_company_name': self.get_company_name,
        })
        
#     def get_company_name(self, invoice_ids):
        
    def get_invoice_obj(self, invoice_ids):
        cr = self.cr
        uid = self.uid
        invoice_objects = self.pool.get('account.invoice').browse(cr, uid,invoice_ids )
        return invoice_objects
    
    def get_total_debit(self, invoice_ids):
        cr = self.cr
        uid = self.uid
        invoice_objects = self.pool.get('account.invoice').browse(cr, uid,invoice_ids )
        total_debit = 0.00
        for invoice_object in invoice_objects: 
            for payment_obj in invoice_object.payment_ids:
                total_debit = total_debit + payment_obj.debit
        return total_debit
    
    def get_total_credit(self, invoice_ids):
        cr = self.cr
        uid = self.uid
        invoice_objects = self.pool.get('account.invoice').browse(cr, uid,invoice_ids )
        total_credit = 0.00
        for invoice_object in invoice_objects: 
            for payment_obj in invoice_object.payment_ids:
                total_credit = total_credit + payment_obj.credit
        return total_credit
    
    def get_debit_total(self, payment_objs):
        cr = self.cr
        uid= self.uid
        total_debit = 0.00
        for payment_obj in payment_objs:
            total_debit = total_debit + payment_obj.debit
        return total_debit
    
    def get_credit_total(self, payment_objs):
        cr = self.cr
        uid= self.uid
        total_credit = 0.00
        for payment_obj in payment_objs:
            total_credit = total_credit + payment_obj.credit
        return total_credit
    
    def get_balance_total(self, payment_objs):
        cr = self.cr
        uid= self.uid
        total_balance = 0.00
        for payment_obj in payment_objs:
            total_balance = total_balance + (payment_obj.debit - payment_obj.credit)
        return total_balance
    
report_sxw.report_sxw('report.collect_report', 'account.invoice', 'addons/sfs_collect_report/report/collect_report.rml', parser=collect_report_acc, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

