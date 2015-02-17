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
#############################################################################

from osv import fields,osv
from openerp import netsvc

class mrp_line_qty_edit(osv.osv_memory):
    _name = "mrp.line.qty.edit"
    
    def _get_default_qty(self, cr, uid, context):
        if context == None:
            context = {}
        return self.pool.get(context.get('active_model')).browse(cr, uid, context.get('active_id'), context=context).product_qty

    _columns = {
                "qty": fields.float("New Quantity", )
            }
    _defaults = {
                 "qty": _get_default_qty              
            }
    
    def update_line_qty(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        res = self.read(cr, uid, ids, context=context)
        active_ids = context.get('active_id')
        model = self.pool.get("stock.move")
        mrp_prod_line = self.pool.get('mrp.production.product.line')
        if active_ids:
            cr.execute("select production_id from mrp_production_move_ids where move_id=%d" % active_ids)
            production_list = cr.fetchall()
            if production_list:
                 production_id = production_list[0] and production_list[0][0]
                 pid = model.browse(cr, uid, active_ids, context=context).product_id.id
                 mrp_prod_ids = mrp_prod_line.search(cr, uid, [('production_id','=',production_id),
                                                              ('product_id','=',pid)], context=context)
                 for mrp_prod_id in mrp_prod_ids:
                    mrp_prod_line.write(cr, uid, mrp_prod_id, {'product_qty': res[0]['qty']}, context=context) 
            model.write(cr, uid, active_ids, {'product_qty': res[0]['qty']}, context=context)
        return True  

class stock_move_consume(osv.osv_memory):
    _inherit = "stock.move.consume"
    def do_move_consume(self, cr, uid, ids, context=None):
         res = {}
         if context == None:
            context = {}
         active_id = context.get('active_id')
         model = self.pool.get("stock.move")
         mrp_model = self.pool.get("mrp.production")
         if active_id:
             production_id = model.browse(cr, uid, active_id, context=context).production_id
             res = super(stock_move_consume, self).do_move_consume(cr, uid, ids, context=context)
             cr.execute("select production_id from mrp_production_move_ids where move_id=%d" % active_id)
             production_list = cr.fetchall()
             if production_list:
                 production_id = production_list[0] and production_list[0][0]
                 if production_id: 
                     wf_service = netsvc.LocalService("workflow")
                     wf_service.trg_validate(uid, 'mrp.production', production_id, 'button_produce_done', cr)
         return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: