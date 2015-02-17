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

from tools.translate import _

class mrp_production_product_line(osv.osv):
    _inherit = 'mrp.production.product.line'
    _columns = {
                'source_bom_id': fields.many2one('mrp.bom', 'Source Bom')
                }
mrp_production_product_line()

class mrp_bom(osv.osv):
    _inherit = 'mrp.bom'
    _columns = {
                'is_sub_assemblies': fields.boolean('Is Sub Assemblies?'),
                'product_code': fields.related('product_id', 'default_code', type="char", size=64,
                                               string='Product Code')
                }
    
    def _check_name_product_name(self, cr, uid, ids, context=None):
        for bom_obj in self.browse(cr, uid, ids, context=context):
            if bom_obj.is_sub_assemblies:
                if bom_obj.product_id.name == bom_obj.name:
                    return False
        return True
    
    _constraints = [
                    (_check_name_product_name, _('BOM name and product name should be different.'),
                     ['name, product_id'])]
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None,
               context=None, count=False):
        if context is None:
            context = {}
        product_pool = self.pool.get('product.product')
        if args and not isinstance(args, list):
            args = [args]
        if not args:
            args = []
        proceed = True
        for domain in args:
            if domain[0] == 'bom_id':
                proceed = False
        if context.get('search_based_on_product', False) and context.get('product_id', False) and proceed:
            product_id = context['product_id']
            product_obj = product_pool.browse(cr, uid, product_id, context=context)
            bom_ids = [x.id for x in product_obj.sub_assembly_bom_ids if product_obj.sub_assembly_bom_ids]
            context['search_based_on_product'] = False
            args.extend([('id', 'in', bom_ids)])
        res = super(mrp_bom, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        return res
    
    def _bom_explode(self, cr, uid, bom, factor, properties=None, addthis=False, level=0, routing_id=False):
        res = super(mrp_bom, self)._bom_explode(cr, uid, bom, factor, properties, addthis, level, routing_id)
        bom_product_lines = res[0]
        for bom_product_line in bom_product_lines:
            if not bom_product_line.get('source_bom_id', False):
                bom_product_line['source_bom_id'] = bom and bom.bom_id and bom.bom_id.id or bom and bom.id or False
        return bom_product_lines, res[1]

mrp_bom()

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    
    def _ref_calc(self, cr, uid, ids, field_names=None, arg=False, context=None):
        res = super(mrp_production, self)._ref_calc(cr, uid, ids, field_names, arg, context=context)
        if field_names:
            for f in field_names:
                if f == 'sale_line_id':
                    for key, value in self._get_sale_ref(cr, uid, ids, 'sale_line_id').items():
                        res[key][f] = value
        return res
    
    def _get_sale_ref(self, cr, uid, ids, field_name=False):
        move_obj = self.pool.get('stock.move')
        res = super(mrp_production, self)._get_sale_ref(cr, uid, ids, field_name)
        productions = self.browse(cr, uid, ids)
        
        def get_parent_move(move_id):
            move = move_obj.browse(cr, uid, move_id)
            if move.move_dest_id:
                return get_parent_move(move.move_dest_id.id)
            return move_id
        
        for production in productions:
            if production.move_prod_id:
                parent_move_line = get_parent_move(production.move_prod_id.id)
                if parent_move_line:
                    move = move_obj.browse(cr, uid, parent_move_line)
                    if field_name == 'sale_line_id':
                        res[production.id] = move.sale_line_id and move.sale_line_id.id or False
        return res
    
    _columns = {
                'sale_line_id': fields.function(_ref_calc, multi='sale_name', type='many2one', relation='sale.order.line',
                                                string='Sale order line', help='Indicate the Reference to sales order line.'),
                'sale_name': fields.function(_ref_calc, multi='sale_name', type='char', string='Sale Name',
                                             help='Indicate the name of sales order.'),
                'sale_ref': fields.function(_ref_calc, multi='sale_name', type='char', string='Sale Reference',
                                            help='Indicate the Customer Reference from sales order.'),
                }
    
    def _action_compute_lines(self, cr, uid, ids, properties=None, context=None):
        res = super(mrp_production, self)._action_compute_lines(cr, uid, ids, properties, context)
        prod_line_obj = self.pool.get('mrp.production.product.line')
        for production in self.browse(cr, uid, ids, context=context):
            if production.sale_line_id:
                for line in production.sale_line_id.assembly_line_ids:
                    data = {
                            'product_uos_qty': False,
                            'name': line.description or '',
                            'product_uom': line.product_uom_id.id or False,
                            'production_id': production.id,
                            'product_qty': line.product_uom_qty or 0.00,
                            'product_uos': False,
                            'product_id': line.product_id.id,
                            'source_bom_id': line.bom_id and line.bom_id.id or False
                            }
                    prod_line_obj.create(cr, uid, data)
                    res.append(data)
        return res
    
    def _make_production_consume_line(self, cr, uid, production_line, parent_move_id, source_location_id=False,
                                      context=None):
        stock_move_pool = self.pool.get('stock.move')
        move_id = super(mrp_production, self)._make_production_consume_line(cr, uid, production_line,
                                                                            parent_move_id, source_location_id,
                                                                            context=context)
        source_bom_id = production_line and production_line.source_bom_id and production_line.source_bom_id.id or \
                                False
        if move_id:
            stock_move_pool.write(cr, uid, move_id, {'source_bom_id': source_bom_id}, context=context)
        return move_id
    
mrp_production()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
