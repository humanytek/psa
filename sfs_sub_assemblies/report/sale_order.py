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

from openerp.report import report_sxw
import pooler
from tools.translate import _

class order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
            'show_discount':self._show_discount,
            'get_order_line': self._get_order_line,
            'get_bom_lines': self._get_bom_lines
        })
        self.bom_data = {}

    def _show_discount(self, uid, context=None):
        cr = self.cr
        try: 
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]
    
    def _get_order_line(self, order_lines):
        res = []
        for order_line in order_lines:
            line_data = {
                         'name': order_line.name or '',
                         'tax': ','.join(map(lambda x: x.name, order_line.tax_id)),
                         'qty': order_line.product_uos and order_line.product_uos_qty or \
                                            order_line.product_uom_qty or 0.00,
                         'uom_name': order_line.product_uos and order_line.product_uos.name or \
                                            order_line.product_uom.name or '',
                         'unit_price': order_line.price_unit or 0.00,
                         'discount': order_line.discount or 0.00,
                         'price_subtotal': order_line.price_subtotal or 0.00,
                         'currency_obj': order_line.order_id.pricelist_id.currency_id,
                         'default_code': order_line.product_id.default_code or False 
                         }
            res.append(line_data)
        return res
    
    def check_product_avail(self, product_id, qty, uom_id):
        pool = pooler.get_pool(self.cr.dbname)
        product_pool = pool.get('product.product')
        if product_id:
            context = {'uom': uom_id}
            product_obj = product_pool.browse(self.cr, self.uid, product_id, context=context)
            qty_available = product_obj.qty_available or 0.00
            if qty_available < qty:
                return False
        return True
    
    def _get_bom_lines(self, order_lines):
        res = []
        for order_line in order_lines:
            for bom_line in order_line.assembly_bom_ids:
                data = {
                        'product_code': bom_line.product_code or '',
                        'product_name': bom_line.product_id.name or '',
                        'availability': _('In Stock')
                        }
                
                res.append(data)
                for product_data in self.bom_data.get(bom_line.id, []):
                    avail = self.check_product_avail(product_data.get('product_id', False), product_data.get('qty', False), product_data.get('uom_id', False))
                    if not avail:
                        data['availability'] = _('Waiting')
                        break
        return res

report_sxw.report_sxw('report.sfs.sale.order.inherit', 'sale.order', 'addons/sfs_sub_assemblies/report/sale_order.rml', parser=order, header="external")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

