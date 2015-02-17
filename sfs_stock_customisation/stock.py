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
##############################################################################

from osv import fields,osv
from tools.translate import _

class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    
    _columns = {
               'user_ids': fields.many2many('res.users', 'warehouse_user_rel', 'user_id', 'warehouse_id', 'Allowed Users')
    }

stock_warehouse()

class stock_move(osv.osv):
    _inherit = "stock.move"
    _columns = {
                'product_categ_id' : fields.related('product_id', 'categ_id', type='many2one', 
                                                    relation="product.category",
                                                    string="Product Category", readonly=True, store=True
                                                    )
                }
    
    def validate_serial_number(self,cr,uid, obj, context=None):
        lot_list = []
        for move in obj.move_lines:
            lot_list.append(move.prodlot_id)
            if len(lot_list)!=len(set(lot_list)):
                return False
        return True
    
    def validate_prod_serial(self, cr, uid, production, context=None):
        production_create_move = production.move_created_ids
        production_create_move.extend(production.move_created_ids2)
        lot_list = []
        for production_move in production_create_move:
            lot_list.append(production_move.prodlot_id)
            if len(lot_list)!=len(set(lot_list)):
                return False
        return True
    
    def _check_serial_number(self, cr, uid, ids, context=None):
        res = True
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.picking_id:
                res = self.validate_serial_number(cr, uid, obj.picking_id,context=context)
            if obj.production_id:
                res = self.validate_prod_serial(cr, uid, obj.production_id, context=context)
        return res

    
    _constraints = [
        (_check_serial_number, _('You cannot assign same serial number for more than one move.'), ['prodlot_id'])]
    
    
stock_move()

class stock_production_lot(osv.osv):
    
    _inherit = "stock.production.lot"
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Serial Number must be unique !'),
    ]
    
stock_production_lot()

class stock_picking(osv.osv):
    
    _inherit = "stock.picking"
    
    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        warehouse_pool = self.pool.get('stock.warehouse')
        full_warehouse_ids = warehouse_pool.search(cr, uid, [], context=context)
        loc_ids = []
        dest_loc_ids = []
        for warehouse in full_warehouse_ids:
            warehouse_record = warehouse_pool.browse(cr, uid, warehouse, context=context)
            user_list = warehouse_record.user_ids
            user_list = [user.id for user in user_list]
            if uid in user_list:
                loc_ids.append(warehouse_record.lot_stock_id)
                loc_ids.append(warehouse_record.lot_input_id)
                loc_ids.append(warehouse_record.lot_output_id)
        for obj in self.browse(cr, uid, ids,context=context):
            if obj.type == 'in':
                for move in obj.move_lines:
                    if not move.location_dest_id in loc_ids:
                        raise osv.except_osv(_('Error!'),  _('You do not have '\
                                'permission to receive the products to the location'
                                ' : %s'%(move.location_dest_id.name)))
            if obj.type == 'out' or obj.type == 'internal':
                for move in obj.move_lines:
                    if not move.location_id in loc_ids:
                        raise osv.except_osv(_('Error!'),  _('You do not have '
                                'permission to deliver the products from the location : %s'%(move.location_id.name)))
        result = super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context=context)
        return result
    
stock_picking()

class stock_location(osv.osv):
    _inherit = "stock.location"

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        res = super(stock_location, self).search(cr, uid, args, offset, limit, order, context=context)
        result = []
        if context.get('source_product'):
            for loc in res:
                loc_record =self.browse(cr, uid, loc, context=context)
                if loc_record.stock_real > 0:
                     result.append(loc)
            return result
        return res
    
stock_location()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: