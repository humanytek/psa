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

class cash_report_acc(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        
        super(cash_report_acc, self).__init__(cr, uid, name, context=context)
        u_name = context['user_id']
        voucher_ids = context['active_ids']
        self.localcontext.update({
            'time': time, 
            'start_date': context['start_date'],
            'end_date': context['end_date'],
            'user_name': u_name,
            'voucher_ids': context['active_ids'],
            'voucher_list': self.get_voucher_obj,
            'get_total': self.get_total,
            'get_logo': self.get_logo,
            'get_cumulative_amount':self.cumulative_amount,
            'get_cum_total': self.cumulative_total,
            'get_term_bills': self.term_bills_total,
            'get_counted_bills': self.counted_bills_total,
        })
        
    def get_voucher_obj(self, voucher_ids):
        cr = self.cr
        uid = self.uid
        data={}
        voucher_objects = self.pool.get('account.voucher').browse(cr, uid,voucher_ids )
        data1=[]
        pool = pooler.get_pool(self.cr.dbname)
        sum = 0.0
        for voucher_obj in voucher_objects:
            cust_obj = voucher_obj.partner_id
            new_data=[]
            line_sum = 0.00
            for pay_line_obj in voucher_obj.line_cr_ids:
                data={}
                jour_obj = pay_line_obj.move_line_id and pay_line_obj.move_line_id.journal_id
                if jour_obj and jour_obj.type == 'sale':
                    for move_line_obj in voucher_obj.move_ids:
                        data={
                            'date': move_line_obj.date,
                            'cus_ref': cust_obj.ref,
                            'cus_name': move_line_obj.partner_id.name,
                            'voucher_name': voucher_obj.number,
                            'v_amount': voucher_obj.amount,
                            'pay_method': voucher_obj.journal_id.name,
                            'inv_paid': move_line_obj.move_id.id
                            }
                    line_sum += pay_line_obj.amount
                if jour_obj and jour_obj.type == 'sale':
                        data['allocation'] = line_sum
            data1.append(data)
            #    if jour_obj and jour_obj.type == 'sale':
            #        data1.append(data)
            for item in data1:
                if not item:
                    data1.remove(item)
                    
        data1 = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in data1)]
        return data1
    
    def get_logo(self):
        cr = self.cr
        uid = self.uid
        company_ids = self.pool.get('res.company').search(cr, uid, [])
        if company_ids:
            company = self.pool.get('res.company').browse(cr, uid, company_ids[0])
            return company.logo
        return True
        
    def get_total(self,voucher_ids):
        cr = self.cr
        uid = self.uid
        sum = 0.00
        voucher_objects = self.pool.get('account.voucher').browse(cr, uid, voucher_ids )
        for voucher_obj in voucher_objects:
            for pay_line_obj in voucher_obj.line_cr_ids:
                jour_obj = pay_line_obj.move_line_id and pay_line_obj.move_line_id.journal_id
                if jour_obj and jour_obj.type == 'sale':
                    sum += pay_line_obj.amount
        return sum
    
    def cumulative_amount(self,voucher_dic):
        cr = self.cr
        uid = self.uid
        sum = 0.00
        list_amt = []
        dict1 = {}
        for amt in voucher_dic:
            if amt.get('pay_method') in dict1:
                dict1[amt.get('pay_method')] += amt.get('allocation',0.00)
            else:
                dict1[amt.get('pay_method')] = amt.get('allocation',0.00)
              
        for item in dict1:
            res_dict = {
                        'method': item,
                        'amount': dict1[item]
                        }
            list_amt.append(res_dict)
        return list_amt
    
    def cumulative_total(self, list_amt):
        sum = 0.00
        for item in list_amt:
            sum += item.get('amount')
        return sum
    
    def term_bills_total(self, u_name ,start_date, end_date):
        cr = self.cr
        uid = self.uid
        u_id = self.pool.get('res.users').search(cr, uid, [('name','=',u_name)])
        amount_total = 0.00
        if u_id:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('create_uid','=', u_id[0]),('state', '!=','paid')])
            for invoice_rec in self.pool.get('account.invoice').browse(cr, uid, invoice_ids):
                if invoice_rec.date_due != invoice_rec.date_invoice and invoice_rec.date_invoice > start_date \
                and invoice_rec.date_invoice < end_date:
                    amount_total = amount_total + invoice_rec.amount_total
        return amount_total

    def counted_bills_total(self, u_name ,start_date, end_date):
        cr = self.cr
        uid = self.uid
        u_id = self.pool.get('res.users').search(cr, uid, [('name','=',u_name)])
        amount_total = 0.00
        if uid:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('create_uid','=', u_id[0]),('state', '=','paid') ])
            for invoice_rec in self.pool.get('account.invoice').browse(cr, uid, invoice_ids):
                if invoice_rec.date_due == invoice_rec.date_invoice and invoice_rec.date_invoice > start_date \
                and invoice_rec.date_invoice < end_date:
                    amount_total = amount_total + invoice_rec.amount_total
        return amount_total
    
report_sxw.report_sxw('report.cash_report', 'account.voucher', 'sfs_cash_report/report/cash_report.rml', parser=cash_report_acc, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

