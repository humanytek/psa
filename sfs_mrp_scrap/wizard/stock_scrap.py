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

class stock_move_scrap(osv.osv_memory):
    _inherit = "stock.move.scrap"
   
    def move_scrap(self, cr, uid, ids, context=None):
        """ To move scrapped products
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        scrap_rec = self.read(cr, uid, ids, context=context)
        stock_move_model = self.pool.get("stock.move")
        active_id = context.get('active_id')
        res = super(stock_move_scrap, self).move_scrap(cr, uid, ids, context=context)
        if active_id and context.get('from_production', False):
            actual_product_qty = stock_move_model.browse(cr, uid, active_id, context=context).product_qty
            remaining_qty =  actual_product_qty - scrap_rec[0]['product_qty']
            stock_move_model.write(cr, uid, active_id, {'product_qty': remaining_qty}, context=context)
            if remaining_qty <= 0.00:
                stock_move_model.action_cancel(cr, uid, [active_id], context=context)
        return res

stock_move_scrap()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: