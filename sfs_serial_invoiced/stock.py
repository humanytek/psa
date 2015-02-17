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

class stock_move_split(osv.osv):
    _inherit = 'stock.move.split'
    
    def onchange_invoice_serial(self, cr, uid, ids, line_exist_ids, user_invoice_serial, context=None):
        res = {}
        res['value'] = {'line_exist_ids': []}
        if user_invoice_serial == True:
            res['value'].update({'use_exist': False}) 
        return res
    
    _columns = {
                'user_invoice_serial': fields.boolean('Use invoiced serial numbers'),
                'related_move_id': fields.many2one('stock.move', 'Related Move')
                }
    
    def onchange_use_exist(self, cr, uid, ids, use_exist, context=None):
        res = {}
        if use_exist == True:
            res['value'] = {'user_invoice_serial': False}
        return res
    
    def split(self, cr, uid, ids, move_ids, context=None):
        """ To split stock moves into serial numbers

        :param move_ids: the ID or list of IDs of stock move we want to split
        """
        if context is None:
            context = {}
        assert context.get('active_model') == 'stock.move',\
             'Incorrect use of the stock move split wizard'
        inventory_id = context.get('inventory_id', False)
        prodlot_obj = self.pool.get('stock.production.lot')
        inventory_obj = self.pool.get('stock.inventory')
        move_obj = self.pool.get('stock.move')
        new_move = []
        for data in self.browse(cr, uid, ids, context=context):
            for move in move_obj.browse(cr, uid, move_ids, context=context):
                move_qty = move.product_qty
                quantity_rest = move.product_qty
                uos_qty_rest = move.product_uos_qty
                new_move = []
                if data.use_exist or data.user_invoice_serial:
                    lines = [l for l in data.line_exist_ids if l]
                else:
                    lines = [l for l in data.line_ids if l]
                total_move_qty = 0.0
                for line in lines:
                    quantity = line.quantity
                    total_move_qty += quantity
                    if total_move_qty > move_qty:
                        raise osv.except_osv(_('Processing Error!'), _('Serial number quantity %d of %s is larger than available quantity (%d)!') \
                                % (total_move_qty, move.product_id.name, move_qty))
                    if quantity <= 0 or move_qty == 0:
                        continue
                    quantity_rest -= quantity
                    uos_qty = quantity / move_qty * move.product_uos_qty
                    uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty
                    if quantity_rest < 0:
                        quantity_rest = quantity
                        self.pool.get('stock.move').log(cr, uid, move.id, _('Unable to assign all lots to this move!'))
                        return False
                    default_val = {
                        'product_qty': quantity,
                        'product_uos_qty': uos_qty,
                        'state': move.state
                    }
                    if quantity_rest > 0:
                        current_move = move_obj.copy(cr, uid, move.id, default_val, context=context)
                        if inventory_id and current_move:
                            inventory_obj.write(cr, uid, inventory_id, {'move_ids': [(4, current_move)]}, context=context)
                        new_move.append(current_move)

                    if quantity_rest == 0:
                        current_move = move.id
                    prodlot_id = False
                    if data.use_exist or data.user_invoice_serial:
                        prodlot_id = line.prodlot_id.id
                    if not prodlot_id:
                        prodlot_id = prodlot_obj.create(cr, uid, {
                            'name': line.name,
                            'product_id': move.product_id.id},
                        context=context)

                    move_obj.write(cr, uid, [current_move], {'prodlot_id': prodlot_id, 'state':move.state})

                    update_val = {}
                    if quantity_rest > 0:
                        update_val['product_qty'] = quantity_rest
                        update_val['product_uos_qty'] = uos_qty_rest
                        update_val['state'] = move.state
                        move_obj.write(cr, uid, [move.id], update_val)

        return new_move
    
stock_move_split()

class stock_move_split_line(osv.osv):
    _inherit = 'stock.move.split.lines'
    
    def onchange_lot_id(self, cr, uid, ids, prodlot_id=False, product_qty=False,
                        loc_id=False, product_id=False, uom_id=False,context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('stock.move')
        res = super(stock_move_split_line, self).onchange_lot_id(cr, uid, ids, prodlot_id, product_qty,
                                                                 loc_id, product_id, uom_id, context=context)
        domain = []
        if context.get('user_invoice_serial', False):
            lot_ids = []
            if context.get('move_id', False):
                move_id = context['move_id']
                move_obj = move_pool.browse(cr, uid, move_id, context=context)
                if move_obj.sale_line_id:
                    sale_line_obj = move_obj.sale_line_id
                    for invoice_line in sale_line_obj.invoice_lines:
                        if invoice_line.production_lot_id:
                            lot_ids.append(invoice_line.production_lot_id.id)
                elif move_obj.purchase_line_id:
                    purchase_line_obj = move_obj.purchase_line_id
                    for invoice_line in purchase_line_obj.invoice_lines:
                        if invoice_line.production_lot_id:
                            lot_ids.append(invoice_line.production_lot_id.id)
            domain.extend([('id', 'in', lot_ids), ('product_id', '=', product_id)])
        else:
            domain.append(('product_id', '=', product_id))
        if not res.get('domain', False):
            res['domain'] = {}
        res['domain'].update({'prodlot_id': domain})
        return res
    
stock_move_split_line()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def split_pack(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','view_split_in_lots')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']
        ctx = context.copy()
        ctx['default_related_move_id'] = ids[0]
        return {
                'name': 'Split in Serial Numbers',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.move.split',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new',
                'nodestroy': True,
                }

stock_move()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
