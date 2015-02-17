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
    _name = "mrp.created.qty.edit"
 
    def _get_default_qty(self, cr, uid, context):
        if context == None:
            context = {}
        return self.pool.get(context.get('active_model')).browse(cr, uid, context.get('active_id'),
                                                                 context=context).product_qty

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
        active_id = context.get('active_id')
        model = self.pool.get("stock.move")
        mrp_model = self.pool.get("mrp.production")
        if active_id:
            move_obj = model.write(cr, uid, active_id, {'product_qty': res[0]['qty']}, context=context)
            model_rec = model.browse(cr, uid, active_id, context=context)
            mrp_rec = model_rec.production_id
            if mrp_rec.product_id == model_rec.product_id:
                mrp_model.write(cr, uid, mrp_rec.id, {'product_qty': res[0]['qty']}, context=context)
        return {
                'type': 'ir.actions.act_close_wizard_and_reload_view'
            } 

class stock_partial_move(osv.osv_memory):
    _inherit = 'stock.partial.move'
    
    def do_partial(self, cr, uid, ids, context=None):
         res = {}
         if context == None:
            context = {}
         active_id = context.get('active_id')
         model = self.pool.get("stock.move")
         if active_id:
             production_id = model.browse(cr, uid, active_id, context=context).production_id.id
             res = super(stock_partial_move, self).do_partial(cr, uid, ids, context=context)
             res.update({'type': 'ir.actions.act_close_wizard_and_reload_view'})
             wf_service = netsvc.LocalService("workflow")
             wf_service.trg_validate(uid, 'mrp.production', production_id, 'button_produce_done', cr)
         return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: