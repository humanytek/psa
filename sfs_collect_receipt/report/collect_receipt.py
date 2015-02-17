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

import time

from openerp.report import report_sxw

class collect_receipt(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(collect_receipt, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                                  'time': time,
                                  'get_move_line_name': self._get_move_line_name,
                                  'get_total_all': self._get_total_all
                                  })
    
    def _get_move_line_name(self, move_line):
        name = ''
        if move_line:
            if move_line.ref:
                name = (move_line.move_id.name or '')+' ('+move_line.ref+')'
            else:
                name = move_line.move_id.name
        return name
    
    def _get_total_all(self, voucher_line_objs):
        amount = 0.00
        for voucher_line in voucher_line_objs:
            amount += voucher_line.amount or 0.00
        return amount

report_sxw.report_sxw('report.collect.receipt', 'account.voucher',
                      'addons/sfs_collect_receipt/report/collect_receipt.rml',
                      parser=collect_receipt, header='internal landscape')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

